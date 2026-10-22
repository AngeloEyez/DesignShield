/**
 * @file elkTopologyLayout.ts
 * @description 基於 ELKjs (Eclipse Layout Kernel) 的現代化電路拓撲排版引擎 (漸進式 POC 模組)
 * 遵循 2026 前端 EDA 原理圖最佳實踐與使用者明確指定之規範：
 * 1. 採用動態按需載入 (Dynamic import) elk.bundled.js，首屏零 Bundle 負擔
 * 2. 採用 Layered 階層流向演算法搭配 FIXED_POS 引腳埠約束與 Orthogonal 曼哈頓直角走線
 * 3. 純前端圖改寫器 (Front-end Graph Rewriter)：
 *    - 依據 1-to-N 匯流/分流關係，自動插入 4x4 Dummy Junction (虛擬焊點節點)
 *    - 走線改寫為 Source -> Junction -> Targets (含主幹與分支)
 *    - 排版完成後將 Junction 座標精確提取為電氣焊點圓點 (Junction Dots)，不進入元件可見清單
 * 4. 單腳測試點 (Test Point TP*) 降權與就近引出：
 *    - 旁路引出並賦予高 shortness 權重，引腳方位對齊主軌，不霸佔主要階層欄位 (Stage Column)
 * 5. Net Name 雙重保障放置：
 *    - ELK 原生 ABOVE 配置 + 水平導線段正上方 4px 幾何錨定，文字底邊永遠不壓線、不切線
 * 6. 4px 平滑微圓角 (Fillet) 與差分對稱分區約束
 */

import {
  type UniversalTopologyData,
  type UniversalTopologyLayout,
  type LayoutNode,
  type LayoutPort,
  type LayoutEdge,
  type JunctionDot,
  type NetLabel,
  type ElectricalSymbol,
  type Point,
  type UniversalPin,
  type UniversalNode,
  type UniversalConnection,
  estimateNodeSize,
  isTestPointNode,
  isDualRailComponent,
  resolvePolarity,
  computeStageColumns,
  assignDiffLogicalUnitsAndBands,
} from './universalTopologyHelpers'

// 單例快取 ELKjs 實例，避免重複實例化
let elkInstance: any = null

/**
 * 動態載入並取得 ELKjs 引擎單例
 *
 * @returns {Promise<any>} ELK 實例
 */
async function getElk(): Promise<any> {
  if (!elkInstance) {
    const { default: ElkConstructor } = await import('elkjs/lib/elk.bundled.js')
    elkInstance = new ElkConstructor()
  }
  return elkInstance
}

/**
 * 將點序列轉換為 SVG 90 度直角正交曼哈頓折線 Path D (純 90 度直角無弧線，符合標準電路拓撲規範)
 *
 * @param {Point[]} points - 折點陣列 (含起點、轉折點與終點)
 * @returns {string} SVG Path d 字串
 */
export function pointsToOrthogonalPath(points: Point[]): string {
  if (points.length === 0) return ''
  // 1. 去除重疊或共線冗餘點
  const cleaned: Point[] = [points[0]]
  for (let i = 1; i < points.length; i++) {
    const prev = cleaned[cleaned.length - 1]
    const cur = points[i]
    if (Math.abs(prev.x - cur.x) > 0.5 || Math.abs(prev.y - cur.y) > 0.5) {
      cleaned.push(cur)
    }
  }

  let d = `M ${cleaned[0].x} ${cleaned[0].y}`
  for (let i = 1; i < cleaned.length; i++) {
    d += ` L ${cleaned[i].x} ${cleaned[i].y}`
  }
  return d
}

// 保持與既有測試相容之別名 (已全面轉為 90 度正交無弧線)
export function pointsToSmoothOrthogonalPath(points: Point[], _radius: number = 0): string {
  return pointsToOrthogonalPath(points)
}

/**
 * 依據原始電路拓撲資料呼叫 ELKjs 進行全量排版運算 (非同步)
 *
 * @param {UniversalTopologyData | Record<string, any> | undefined} inputData - 原始拓撲資料
 * @returns {Promise<UniversalTopologyLayout>} 完整 SVG 幾何排版結果
 */
export async function computeElkTopologyLayout(
  inputData: UniversalTopologyData | Record<string, any> | undefined
): Promise<UniversalTopologyLayout> {
  const fallback: UniversalTopologyLayout = {
    width: 320,
    height: 120,
    title: '',
    channelType: 'single',
    nodes: [],
    edges: [],
    junctionDots: [],
    netLabels: [],
    symbols: [],
  }

  if (!inputData) return fallback

  const raw = inputData as Record<string, any>
  const data: UniversalTopologyData = raw.topology ? raw.topology : (raw as UniversalTopologyData)
  if (!Array.isArray(data.nodes) || data.nodes.length === 0) {
    return fallback
  }

  const elk = await getElk()
  const channelType = data.channel_type || 'single'
  const isDiff = channelType === 'differential'
  const title = data.title || ''

  // 1. 引腳極性快速查找映射
  const pinPolarityMap = new Map<string, 'p' | 'n'>()
  for (const c of data.connections) {
    const pol = resolvePolarity(c.rail_id, c.net_name)
    if (c.from_node && c.from_pin) pinPolarityMap.set(`${c.from_node}#${c.from_pin}`, pol)
    if (c.to_node && c.to_pin) pinPolarityMap.set(`${c.to_node}#${c.to_pin}`, pol)
  }

  const getPinPol = (nodeId: string, pin: UniversalPin, idx: number): 'p' | 'n' => {
    const key = `${nodeId}#${pin.pin_number}`
    if (pinPolarityMap.has(key)) return pinPolarityMap.get(key)!
    const name = pin.pin_name || ''
    if (/(?:_N|_DN|_DM|D-)(?:\b|\d+|_|$)/i.test(name) || /-(?:\b|\d+|_|$)/.test(name)) return 'n'
    if (/(?:_P|_DP|D\+)(?:\b|\d+|_|$)/i.test(name) || /\+(?:\b|\d+|_|$)/.test(name)) return 'p'
    return idx % 2 === 1 ? 'n' : 'p'
  }

  // 1B. 差分雙軌通道：導入自研雙軌邏輯單元與路徑帶 (Path Bands) 分配演算法
  let nodeBandMap = new Map<string, number>()
  let nodeColMap = new Map<string, number>()
  if (isDiff) {
    const rawMainNodes = data.nodes
    const outgoingFlowCount = new Map<string, number>()
    for (const c of data.connections) {
      outgoingFlowCount.set(c.from_node, (outgoingFlowCount.get(c.from_node) || 0) + 1)
    }
    const mainNodes = rawMainNodes.filter(
      (n) => !(n.pins.length === 1 && isTestPointNode(n) && (outgoingFlowCount.get(n.id) || 0) === 0)
    )
    const mainNodeIdSet = new Set(mainNodes.map((n) => n.id))
    const flowConnections = data.connections.filter(
      (c) => mainNodeIdSet.has(c.from_node) && mainNodeIdSet.has(c.to_node) && c.from_node !== c.to_node
    )
    const { stages, nodeColMap: calculatedColMap } = computeStageColumns(mainNodes, flowConnections)
    nodeColMap = calculatedColMap
    const nodeById = new Map<string, UniversalNode>(data.nodes.map((n) => [n.id, n]))
    const nodeOrderMap = new Map<string, number>(data.nodes.map((n, i) => [n.id, i]))
    const bandResult = assignDiffLogicalUnitsAndBands({
      stages,
      nodeById,
      nodeOrderMap,
      flowConnections,
      allConnections: data.connections,
      compactTpNodes: [],
      getPinPolarity: (nodeId, pin, idx) => getPinPol(nodeId, pin, idx),
      pBaseY: 65,
      nBaseY: 115,
    })
    nodeBandMap = bandResult.nodeBandMap
  }

  // 2. 構建 ELK 節點與引腳 (全量圖論化：主元件、被動元件、VCC、GND、測試點全數納入)
  const elkChildren: any[] = []
  const nodeRoleMap = new Map<string, string>()
  const nodeSizeMap = new Map<string, { width: number; height: number }>()

  for (const node of data.nodes) {
    const isSingleTp = isTestPointNode(node) && node.pins.length === 1
    let { width, height } = estimateNodeSize(node, isSingleTp)
    const isTerminal = node.role === 'terminal'
    const isDual = isDualRailComponent(node)
    if (isDiff && isTerminal && isDual) {
      // 差分端點 IC / Connector: 跨越 P 軌與 N 軌，引腳高度完全對齊主路徑串聯被動元件引腳
      // 標準串聯電阻 pin Y 距頂端為 19px，雙軌中心差為 70px (P 於 32, N 於 102)
      // 因此端點高度設為 110px，P 引腳置於 20px，N 引腳置於 90px (跨度 70px 完美水平平齊)
      height = 110
    }
    nodeRoleMap.set(node.id, node.role)
    nodeSizeMap.set(node.id, { width, height })

    // 設定引腳相對座標與方位 (WEST=入端, EAST=出端, NORTH=頂部, SOUTH=底部)
    const elkPorts: any[] = []
    const isPullUp = node.role === 'pull_up'
    const isShunt = node.role === 'shunt_ground' || node.role === 'pull_down'

    if (isSingleTp) {
      // 單腳測試點：單埠居中，依極性設定方位 (width: 0, height: 0 確保導線無縫錨定)
      // 正極 (P) 位於上側，信號自下方接通，引腳埠朝南 (SOUTH)
      // 負極 (N) 位於下側，信號自上方接通，引腳埠朝北 (NORTH)
      const pol = node.pins[0] ? getPinPol(node.id, node.pins[0], 0) : 'p'
      elkPorts.push({
        id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
        width: 0,
        height: 0,
        x: Math.round(width / 2),
        y: pol === 'p' ? height : 0,
        layoutOptions: {
          'elk.port.side': pol === 'p' ? 'SOUTH' : 'NORTH',
        },
      })
    } else if (isPullUp) {
      elkPorts.push({
        id: `${node.id}_2`,
        width: 0,
        height: 0,
        x: Math.round(width / 2),
        y: 0,
        layoutOptions: { 'elk.port.side': 'NORTH' },
      })
      elkPorts.push({
        id: `${node.id}_1`,
        width: 0,
        height: 0,
        x: Math.round(width / 2),
        y: height,
        layoutOptions: { 'elk.port.side': 'SOUTH' },
      })
    } else if (isShunt) {
      elkPorts.push({
        id: `${node.id}_1`,
        width: 0,
        height: 0,
        x: Math.round(width / 2),
        y: 0,
        layoutOptions: { 'elk.port.side': 'NORTH' },
      })
      elkPorts.push({
        id: `${node.id}_2`,
        width: 0,
        height: 0,
        x: Math.round(width / 2),
        y: height,
        layoutOptions: { 'elk.port.side': 'SOUTH' },
      })
    } else if (isDiff && isTerminal) {
      // 差分端點 IC / Connector: 跨越 P 軌與 N 軌，引腳高度完全對齊主路徑串聯被動元件引腳
      const pPins = node.pins.filter((p, i) => getPinPol(node.id, p, i) === 'p')
      const nPins = node.pins.filter((p, i) => getPinPol(node.id, p, i) === 'n')
      const isSrc = data.connections.some((c) => c.from_node === node.id)
      const portSide = isSrc ? 'EAST' : 'WEST'
      const portRelX = isSrc ? width : 0

      pPins.forEach((pin, pIdx) => {
        const relY = Math.round(isDual ? 20 + pIdx * 16 : height * 0.28 + pIdx * 16)
        elkPorts.push({
          id: `${node.id}_${pin.pin_number}`,
          width: 0,
          height: 0,
          x: portRelX,
          y: relY,
          layoutOptions: { 'elk.port.side': portSide },
        })
      })
      nPins.forEach((pin, nIdx) => {
        const relY = Math.round(isDual ? 90 + nIdx * 16 : height * 0.72 + nIdx * 16)
        elkPorts.push({
          id: `${node.id}_${pin.pin_number}`,
          width: 0,
          height: 0,
          x: portRelX,
          y: relY,
          layoutOptions: { 'elk.port.side': portSide },
        })
      })
    } else if (node.pins.length >= 4) {
      // 4-pin CMC 共模扼流圈 或 IC (中繼 IC 緊湊排版)
      const isIc = (node.category || '').toLowerCase() === 'ic'
      node.pins.forEach((p, idx) => {
        const isLeft = p.orientation === 'left' || idx === 0 || idx === 2
        const pol = getPinPol(node.id, p, idx)
        const relX = isLeft ? 0 : width
        // 若為 IC：Pin 1(P) 排在 36px，Pin 2(N) 排在 60px；與頂部 Header (y=13) 保持 23px 淨空，絕不重疊
        // 若為標準 CMC (height 38px)：維持 28% 與 72%
        let relY: number
        if (isIc && height >= 68) {
          relY = pol === 'p' ? 36 : 60
        } else {
          relY = pol === 'p' ? Math.round(height * 0.28) : Math.round(height * 0.72)
        }
        elkPorts.push({
          id: `${node.id}_${p.pin_number}`,
          width: 0,
          height: 0,
          x: relX,
          y: relY,
          layoutOptions: { 'elk.port.side': isLeft ? 'WEST' : 'EAST' },
        })
      })
    } else {
      // 一般 2-pin 串聯被動元件 (電阻、電容)
      node.pins.forEach((p, idx) => {
        const isLeft = p.orientation === 'left' || idx === 0
        elkPorts.push({
          id: `${node.id}_${p.pin_number}`,
          width: 0,
          height: 0,
          x: isLeft ? 0 : width,
          y: Math.round(height / 2),
          layoutOptions: { 'elk.port.side': isLeft ? 'WEST' : 'EAST' },
        })
      })
    }

    // 優先級與分區權重配置
    let nodePriority = '5'
    if (isTerminal) nodePriority = '10'
    else if (node.role === 'series') nodePriority = '8'
    else if (isPullUp || isShunt) nodePriority = '2'
    else if (isSingleTp) nodePriority = '1' // 單腳測試點降為最低優先級，避免撐開欄位

    // 差分對稱分區與路徑帶約束：
    // 取得自研 Stage Column 與 Path Band
    let col = nodeColMap.get(node.id)
    if (col === undefined) {
      // 若為單腳測試點等未納入主圖之分支節點，對齊其關聯來源節點之欄位
      const incomingConn = data.connections.find((c) => c.to_node === node.id)
      if (incomingConn) {
        col = nodeColMap.get(incomingConn.from_node) ?? 0
      } else {
        col = 0
      }
    }

    // 計算 semiInteractive 跨層與層內順序之 hintY 座標：
    // 正極 (P) 於上方 (y 小)，負極 (N) 於下方 (y 大)；
    // 主路徑 Band 0 居頂部，旁路/CMC/Hub Band 1 位於下側 (y 大)，杜絕 CMC 插入電阻中間
    let hintY = 0
    if (isDiff) {
      const band = nodeBandMap.get(node.id) ?? 0
      if (isSingleTp) {
        const pol = node.pins[0] ? getPinPol(node.id, node.pins[0], 0) : 'p'
        hintY = pol === 'p' ? band * 200 - 50 : band * 200 + 120
      } else if (isDualRailComponent(node)) {
        hintY = band * 200 + 35
      } else {
        const firstPinPol = node.pins[0] ? getPinPol(node.id, node.pins[0], 0) : 'p'
        hintY = band * 200 + (firstPinPol === 'p' ? 10 : 60)
      }
    }

    const hintX = col * 200
    const nodeLayoutOptions: Record<string, string> = {
      'elk.portConstraints': 'FIXED_POS',
      'elk.priority': nodePriority,
    }
    if (isDiff) {
      nodeLayoutOptions['org.eclipse.elk.layered.layering.layerId'] = String(col * 2)
      nodeLayoutOptions['org.eclipse.elk.position'] = `(${hintX}, ${hintY})`
    }

    elkChildren.push({
      id: node.id,
      width,
      height,
      x: hintX,
      y: hintY,
      ports: elkPorts,
      layoutOptions: nodeLayoutOptions,
    })
  }

  // 3. 純前端圖改寫器 (Graph Rewriter)：
  // 針對差分訊號一對多 (如 DDR DQS 同時驅動 XMM4 與 XMM3，或驅動 + 差分測點)，採用虛擬差分匯流排節點 (Differential Pair Bus Node)
  // 將 P/N 軌引腳高度與平行間隙固化在同一節點上，徹底杜絕負極線上下階梯繞路與分支交叉問題
  const elkEdges: any[] = []
  const edgeMetaMap = new Map<
    string,
    {
      netName?: string
      railId?: string
      sourceId: string
      targetId: string
      isBranch: boolean
      polarity: 'p' | 'n'
      isTestPointStub: boolean
    }
  >()

  const juncPolarityMap = new Map<string, 'p' | 'n'>()
  let edgeCounter = 0

  // 3A. 前置匯流分析 (Inflow Merge Junctions)：
  // 若多條導線匯入同一個目標引腳 (如主幹 KR135 與旁路 KR129 同時匯入 UR800 引腳 1)，
  // 建立前置匯流虛擬節點 merge_junc_${toNode}_${toPin}
  const connsByTargetPin = new Map<string, UniversalConnection[]>()
  for (const c of data.connections) {
    const tgtKey = `${c.to_node}_${c.to_pin}`
    if (!connsByTargetPin.has(tgtKey)) connsByTargetPin.set(tgtKey, [])
    connsByTargetPin.get(tgtKey)!.push(c)
  }

  const mergeJunctions = new Map<
    string,
    {
      juncId: string
      targetNodeId: string
      targetPin: string
      polarity: 'p' | 'n'
      targetCol: number
      targetBand: number
    }
  >()

  const mergeSourcePins = new Map<string, string>() // fromKey -> juncId
  for (const [tgtKey, tConns] of connsByTargetPin.entries()) {
    if (tConns.length > 1) {
      const firstConn = tConns[0]
      const toNode = firstConn.to_node
      const toNodeObj = data.nodes.find((n) => n.id === toNode)
      // 僅對中繼串聯被動元件 (如 UR800/UR801) 建立前置匯流節點，終端連接器或 IC (terminal) 維持各自接入引腳
      if (toNodeObj && toNodeObj.role !== 'series') continue

      const pol = resolvePolarity(firstConn.rail_id, firstConn.net_name)
      const toPin = firstConn.to_pin
      const targetCol = nodeColMap.get(toNode) ?? 0
      const targetBand = nodeBandMap.get(toNode) ?? 0
      const juncId = `merge_junc_${toNode}_${toPin}`

      mergeJunctions.set(tgtKey, {
        juncId,
        targetNodeId: toNode,
        targetPin: toPin,
        polarity: pol,
        targetCol,
        targetBand,
      })

      for (const c of tConns) {
        mergeSourcePins.set(`${c.from_node}_${c.from_pin}`, juncId)
      }

      const mergeHintX = targetCol * 200 - 36
      const mergeHintY = pol === 'p' ? targetBand * 200 + 10 : targetBand * 200 + 60
      const mergeLayerId = Math.max(0, targetCol * 2 - 1)

      elkChildren.push({
        id: juncId,
        width: 4,
        height: 4,
        x: mergeHintX,
        y: mergeHintY,
        ports: [
          {
            id: `${juncId}_in`,
            width: 0,
            height: 0,
            x: 0,
            y: 2,
            layoutOptions: { 'elk.port.side': 'WEST' },
          },
          {
            id: `${juncId}_tap`,
            width: 0,
            height: 0,
            x: 2,
            y: 4,
            layoutOptions: { 'elk.port.side': 'SOUTH' },
          },
          {
            id: `${juncId}_branch`,
            width: 0,
            height: 0,
            x: 2,
            y: 4,
            layoutOptions: { 'elk.port.side': 'SOUTH' },
          },
          {
            id: `${juncId}_out`,
            width: 0,
            height: 0,
            x: 4,
            y: 2,
            layoutOptions: { 'elk.port.side': 'EAST' },
          },
        ],
        layoutOptions: {
          'elk.portConstraints': 'FIXED_POS',
          'elk.priority': '10',
          ...(isDiff
            ? {
                'org.eclipse.elk.layered.layering.layerId': String(mergeLayerId),
                'org.eclipse.elk.position': `(${mergeHintX}, ${mergeHintY})`,
              }
            : {}),
        },
      })

      // 建立 merge_junc 到目標引腳的直通短邊
      const mergeOutEdgeId = `edge_${edgeCounter++}`
      elkEdges.push({
        id: mergeOutEdgeId,
        sources: [`${juncId}_out`],
        targets: [`${toNode}_${toPin}`],
        labels: [],
        layoutOptions: {
          'elk.priority': '10',
          'elk.layered.priority.straightness': '10',
          'elk.layered.priority.shortness': '10',
        },
      })
      edgeMetaMap.set(mergeOutEdgeId, {
        netName: firstConn.net_name,
        railId: firstConn.rail_id,
        sourceId: juncId,
        targetId: toNode,
        isBranch: false,
        polarity: pol,
        isTestPointStub: false,
      })

      juncPolarityMap.set(juncId, pol)
    }
  }

  // 輔助函式：解析連線之最終目標引腳（若匯入 merge_junc 則重定向至其輸入或分支引腳）
  const resolveTarget = (c: UniversalConnection) => {
    const mergeInfo = mergeJunctions.get(`${c.to_node}_${c.to_pin}`)
    if (mergeInfo) {
      const isBranch = Boolean(c.is_branch) || (nodeBandMap.get(c.from_node) ?? 0) > 0
      return {
        portId: isBranch ? `${mergeInfo.juncId}_tap` : `${mergeInfo.juncId}_in`,
        targetId: mergeInfo.juncId,
        isBranch,
      }
    }
    return {
      portId: `${c.to_node}_${c.to_pin}`,
      targetId: c.to_node,
      isBranch: Boolean(c.is_branch),
    }
  }

  // 輔助函式：配置邊線直線約束與優先級權重
  const getEdgeOptions = (isMainTrunk: boolean, isSingleTp: boolean) => {
    const options: Record<string, string> = {
      'elk.priority': isSingleTp ? '1' : isMainTrunk ? '10' : '1',
    }
    if (isMainTrunk) {
      options['elk.layered.priority.straightness'] = '10'
      options['elk.layered.priority.shortness'] = '10'
    } else if (isSingleTp) {
      options['elk.layered.priority.shortness'] = '10'
    }
    return options
  }

  // 依來源節點分組
  const connsBySource = new Map<string, UniversalConnection[]>()
  for (const c of data.connections) {
    if (!connsBySource.has(c.from_node)) connsBySource.set(c.from_node, [])
    connsBySource.get(c.from_node)!.push(c)
  }

  for (const [srcNodeId, conns] of connsBySource.entries()) {
    const srcNode = data.nodes.find((n) => n.id === srcNodeId)
    if (!srcNode) continue

    const srcSize = nodeSizeMap.get(srcNodeId) || { width: 100, height: 52 }
    const isDual = isDualRailComponent(srcNode)
    const pConns = conns.filter((c) => resolvePolarity(c.rail_id, c.net_name) === 'p')
    const nConns = conns.filter((c) => resolvePolarity(c.rail_id, c.net_name) === 'n')
    // 嚴格限制：僅有跨雙軌之端點/中繼元件且 P/N 軌同時存在且有分流時，才建立雙軌 diff_bus
    const isDiffFanout =
      isDiff &&
      isDual &&
      pConns.length > 0 &&
      nConns.length > 0 &&
      (pConns.length > 1 || nConns.length > 1)

    if (isDiffFanout) {
      // 差分一對多匯流排分岔節點 (Differential Pair Bus Node)
      const busId = `diff_bus_${srcNodeId}`
      const busHeight = srcSize.height
      const relY_p = Math.round(srcSize.height >= 90 ? 20 : busHeight * 0.28)
      const relY_n = Math.round(srcSize.height >= 90 ? 90 : busHeight * 0.72)

      const busPorts: any[] = [
        // WEST 輸入端 (接收來自來源晶片的 P/N 信號)
        { id: `${busId}_p_in`, width: 0, height: 0, x: 0, y: relY_p, layoutOptions: { 'elk.port.side': 'WEST' } },
        { id: `${busId}_n_in`, width: 0, height: 0, x: 0, y: relY_n, layoutOptions: { 'elk.port.side': 'WEST' } },
        // EAST 直通主幹輸出端 (通往下一個主要接收晶片)
        { id: `${busId}_p_trunk`, width: 0, height: 0, x: 4, y: relY_p, layoutOptions: { 'elk.port.side': 'EAST' } },
        { id: `${busId}_n_trunk`, width: 0, height: 0, x: 4, y: relY_n, layoutOptions: { 'elk.port.side': 'EAST' } },
        // SOUTH 下沉分支 (通往下側次要端點晶片/次軌) - N 靠左(x:0)、P 靠右(x:4)，雙車道完美平行絕不交叉
        { id: `${busId}_p_branch_down`, width: 0, height: 0, x: 4, y: busHeight, layoutOptions: { 'elk.port.side': 'SOUTH' } },
        { id: `${busId}_n_branch_down`, width: 0, height: 0, x: 0, y: busHeight, layoutOptions: { 'elk.port.side': 'SOUTH' } },
        // NORTH 上升分支 (通往上側測試點 TP)
        { id: `${busId}_p_branch_up`, width: 0, height: 0, x: 4, y: 0, layoutOptions: { 'elk.port.side': 'NORTH' } },
        { id: `${busId}_n_branch_up`, width: 0, height: 0, x: 0, y: 0, layoutOptions: { 'elk.port.side': 'NORTH' } },
      ]

      const srcCol = nodeColMap.get(srcNodeId) ?? 0
      const srcBand = nodeBandMap.get(srcNodeId) ?? 0
      // 緊鄰下一級電阻引腳前方約 36px (留給 pin 腳呼吸空間)
      const busHintX = (srcCol + 1) * 200 - 36
      const busHintY = srcBand * 200 + 35

      elkChildren.push({
        id: busId,
        width: 4,
        height: busHeight,
        x: busHintX,
        y: busHintY,
        ports: busPorts,
        layoutOptions: {
          'elk.portConstraints': 'FIXED_POS',
          'elk.priority': '8',
          'org.eclipse.elk.layered.layering.layerId': String(srcCol * 2 + 1),
          'org.eclipse.elk.position': `(${busHintX}, ${busHintY})`,
        },
      })

      // 3A. 建立來源到 Bus 節點的直通入邊 (P & N)
      const pMainConn = pConns.find((c) => !c.is_branch) || pConns[0]
      const nMainConn = nConns.find((c) => !c.is_branch) || nConns[0]

      if (pMainConn) {
        const inEdgeId = `edge_${edgeCounter++}`
        const netName = pMainConn.net_name || ''
        elkEdges.push({
          id: inEdgeId,
          sources: [`${pMainConn.from_node}_${pMainConn.from_pin}`],
          targets: [`${busId}_p_in`],
          labels: [],
          layoutOptions: getEdgeOptions(true, false),
        })
        edgeMetaMap.set(inEdgeId, {
          netName,
          railId: pMainConn.rail_id,
          sourceId: pMainConn.from_node,
          targetId: busId,
          isBranch: false,
          polarity: 'p',
          isTestPointStub: false,
        })
      }

      if (nMainConn) {
        const inEdgeId = `edge_${edgeCounter++}`
        const netName = nMainConn.net_name || ''
        elkEdges.push({
          id: inEdgeId,
          sources: [`${nMainConn.from_node}_${nMainConn.from_pin}`],
          targets: [`${busId}_n_in`],
          labels: [],
          layoutOptions: getEdgeOptions(true, false),
        })
        edgeMetaMap.set(inEdgeId, {
          netName,
          railId: nMainConn.rail_id,
          sourceId: nMainConn.from_node,
          targetId: busId,
          isBranch: false,
          polarity: 'n',
          isTestPointStub: false,
        })
      }

      // 3B. 建立 Bus 節點到各 Targets 的出邊 (主幹直行、分支下沉/上升)
      const processDiffOut = (cList: UniversalConnection[], pol: 'p' | 'n') => {
        cList.forEach((c) => {
          const tgtNode = data.nodes.find((n) => n.id === c.to_node)
          if (!tgtNode) return

          const isSingleTp = isTestPointNode(tgtNode) && tgtNode.pins.length === 1
          const tgt = resolveTarget(c)
          const isBranch = tgt.isBranch
          const outEdgeId = `edge_${edgeCounter++}`

          let srcPortId: string
          if (!isBranch && !isSingleTp) {
            srcPortId = pol === 'p' ? `${busId}_p_trunk` : `${busId}_n_trunk`
          } else if (isSingleTp) {
            srcPortId = pol === 'p' ? `${busId}_p_branch_up` : `${busId}_n_branch_down`
          } else {
            srcPortId = pol === 'p' ? `${busId}_p_branch_down` : `${busId}_n_branch_down`
          }

          const isMainTrunk = !isBranch && !isSingleTp && (nodeBandMap.get(srcNodeId) ?? 0) === 0
          const edgeOptions = getEdgeOptions(isMainTrunk, isSingleTp)

          elkEdges.push({
            id: outEdgeId,
            sources: [srcPortId],
            targets: [tgt.portId],
            labels: [],
            layoutOptions: edgeOptions,
          })
          edgeMetaMap.set(outEdgeId, {
            netName: c.net_name,
            railId: c.rail_id,
            sourceId: busId,
            targetId: tgt.targetId,
            isBranch,
            polarity: pol,
            isTestPointStub: isSingleTp,
          })
        })
      }

      processDiffOut(pConns, 'p')
      processDiffOut(nConns, 'n')
    } else {
      // 非差分一對多：依據出發引腳 (from_pin) 分組處理單端分流或 1-to-1 直連
      const connsByPin = new Map<string, UniversalConnection[]>()
      for (const c of conns) {
        if (!connsByPin.has(c.from_pin)) connsByPin.set(c.from_pin, [])
        connsByPin.get(c.from_pin)!.push(c)
      }

      for (const [fromPin, pinConns] of connsByPin.entries()) {
        const fromPinKey = `${srcNodeId}_${fromPin}`
        const associatedMergeJuncId = mergeSourcePins.get(fromPinKey)

        if (associatedMergeJuncId && pinConns.length > 1) {
          // 當此引腳已有直通連線連入 merge_junc 時，分支連線直接由 merge_junc 樞紐引出，
          // 杜絕串聯兩個 Dummy Node 導致的層級撕裂與假雙焊點！
          const trunkConn = pinConns.find((c) => mergeJunctions.has(`${c.to_node}_${c.to_pin}`)) || pinConns[0]
          const branchConns = pinConns.filter((c) => c !== trunkConn)

          // 1. 建立 srcNode 到 merge_junc 的主幹連線
          const tgt = resolveTarget(trunkConn)
          const trunkEdgeId = `edge_${edgeCounter++}`
          const isMainTrunk = (nodeBandMap.get(srcNodeId) ?? 0) === 0
          elkEdges.push({
            id: trunkEdgeId,
            sources: [`${srcNodeId}_${fromPin}`],
            targets: [tgt.portId],
            labels: [],
            layoutOptions: getEdgeOptions(isMainTrunk, false),
          })
          edgeMetaMap.set(trunkEdgeId, {
            netName: trunkConn.net_name,
            railId: trunkConn.rail_id,
            sourceId: srcNodeId,
            targetId: tgt.targetId,
            isBranch: false,
            polarity: resolvePolarity(trunkConn.rail_id, trunkConn.net_name),
            isTestPointStub: false,
          })

          // 2. 分支連線直接由 merge_junc 的 SOUTH 端口引出
          for (const bConn of branchConns) {
            const bTgtNode = data.nodes.find((n) => n.id === bConn.to_node)
            if (!bTgtNode) continue
            const bEdgeId = `edge_${edgeCounter++}`
            const bPol = resolvePolarity(bConn.rail_id, bConn.net_name)
            elkEdges.push({
              id: bEdgeId,
              sources: [`${associatedMergeJuncId}_branch`],
              targets: [`${bConn.to_node}_${bConn.to_pin}`],
              labels: [],
              layoutOptions: getEdgeOptions(false, false),
            })
            edgeMetaMap.set(bEdgeId, {
              netName: bConn.net_name,
              railId: bConn.rail_id,
              sourceId: associatedMergeJuncId,
              targetId: bConn.to_node,
              isBranch: true,
              polarity: bPol,
              isTestPointStub: false,
            })
          }
          continue
        }

        const firstConn = pinConns[0]
        const pol = resolvePolarity(firstConn.rail_id, firstConn.net_name)

        if (pinConns.length > 1) {
          // 1-to-N 單端或單腳分流：建立 Dummy Junction 虛擬節點 (對齊 netlistsvg 標準作法)
          const juncId = `junc_${srcNodeId}_${fromPin}`
          juncPolarityMap.set(juncId, pol)
          const srcCol = nodeColMap.get(srcNodeId) ?? 0
          const srcBand = nodeBandMap.get(srcNodeId) ?? 0
          const juncHintX = (srcCol + 1) * 200 - 36
          const juncHintY = pol === 'p' ? srcBand * 200 + 10 : srcBand * 200 + 60
          const juncLayoutOptions: Record<string, string> = {
            'elk.portConstraints': 'FIXED_POS',
            'elk.priority': '8',
          }
          if (isDiff) {
            juncLayoutOptions['org.eclipse.elk.layered.layering.layerId'] = String(srcCol * 2 + 1)
            juncLayoutOptions['org.eclipse.elk.position'] = `(${juncHintX}, ${juncHintY})`
          }

          elkChildren.push({
            id: juncId,
            width: 4,
            height: 4,
            x: juncHintX,
            y: juncHintY,
            ports: [
              {
                id: `${juncId}_in`,
                width: 0,
                height: 0,
                x: 0,
                y: 2,
                layoutOptions: { 'elk.port.side': 'WEST' },
              },
              {
                id: `${juncId}_out`,
                width: 0,
                height: 0,
                x: 4,
                y: 2,
                layoutOptions: { 'elk.port.side': 'EAST' },
              },
              {
                id: `${juncId}_tap`,
                width: 0,
                height: 0,
                x: 2,
                y: 2,
                layoutOptions: { 'elk.port.side': 'SOUTH' },
              },
            ],
            layoutOptions: juncLayoutOptions,
          })

          // 入端主邊：Source -> Dummy Junction
          const inEdgeId = `edge_${edgeCounter++}`
          const mainConn = pinConns.find((c) => !c.is_branch) || pinConns[0]
          const netName = mainConn.net_name || ''
          const isMainTrunkIn = (nodeBandMap.get(srcNodeId) ?? 0) === 0
          elkEdges.push({
            id: inEdgeId,
            sources: [`${srcNodeId}_${fromPin}`],
            targets: [`${juncId}_in`],
            labels: [],
            layoutOptions: getEdgeOptions(isMainTrunkIn, false),
          })
          edgeMetaMap.set(inEdgeId, {
            netName,
            railId: mainConn.rail_id,
            sourceId: srcNodeId,
            targetId: juncId,
            isBranch: false,
            polarity: pol,
            isTestPointStub: false,
          })

          // 出端邊：Dummy Junction -> Targets
          pinConns.forEach((c) => {
            const tgtNode = data.nodes.find((n) => n.id === c.to_node)
            if (!tgtNode) return
            const isSingleTp = isTestPointNode(tgtNode) && tgtNode.pins.length === 1
            const tgt = resolveTarget(c)
            const isBranch = tgt.isBranch
            const isTap = isSingleTp || isBranch
            const outEdgeId = `edge_${edgeCounter++}`
            const srcPortId = isTap ? `${juncId}_tap` : `${juncId}_out`
            const isMainTrunk = !isBranch && !isSingleTp && (nodeBandMap.get(srcNodeId) ?? 0) === 0
            const edgeOptions = getEdgeOptions(isMainTrunk, isSingleTp)

            elkEdges.push({
              id: outEdgeId,
              sources: [srcPortId],
              targets: [tgt.portId],
              labels: [],
              layoutOptions: edgeOptions,
            })
            edgeMetaMap.set(outEdgeId, {
              netName: c.net_name,
              railId: c.rail_id,
              sourceId: juncId,
              targetId: tgt.targetId,
              isBranch,
              polarity: pol,
              isTestPointStub: isSingleTp,
            })
          })
        } else {
          // 1-to-1 直接連線
          const c = pinConns[0]
          const tgtNode = data.nodes.find((n) => n.id === c.to_node)
          if (!tgtNode) continue
          const isSingleTp = isTestPointNode(tgtNode) && tgtNode.pins.length === 1
          const tgt = resolveTarget(c)
          const isBranch = tgt.isBranch
          const netName = c.net_name || ''
          const directEdgeId = `edge_${edgeCounter++}`

          const isMainTrunk = !isBranch && !isSingleTp && (nodeBandMap.get(srcNodeId) ?? 0) === 0
          const edgeOptions = getEdgeOptions(isMainTrunk, isSingleTp)

          elkEdges.push({
            id: directEdgeId,
            sources: [`${srcNodeId}_${fromPin}`],
            targets: [tgt.portId],
            labels: [],
            layoutOptions: edgeOptions,
          })
          edgeMetaMap.set(directEdgeId, {
            netName,
            railId: c.rail_id,
            sourceId: srcNodeId,
            targetId: tgt.targetId,
            isBranch,
            polarity: pol,
            isTestPointStub: isSingleTp,
          })
        }
      }
    }
  }

  // 依據是否有 Net Name 標籤動態配置層級淨間距：
  // 邊線採幾何純文字後處理錨定 (不傳入虛擬 Label 物件至 ELK，杜絕同層節點被字串推擠錯位)；
  // 因此 nodeNodeBetweenLayers 預留 96px 作為導線與 Net Name 文字標籤之標準水平可視間距；
  // 若完全無標籤，則預留緊湊標準間距 45px。
  const hasLabels = data.connections.some((c) => Boolean(c.net_name && !c.is_branch))
  const layerSpacing = hasLabels ? '96' : '45'

  // 4. 執行 ELKjs 全量圖論排版
  const elkGraph = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.edgeRouting': 'ORTHOGONAL',
      'elk.layered.spacing.nodeNodeBetweenLayers': layerSpacing,
      'elk.spacing.nodeNode': '32',
      'elk.spacing.edgeEdge': '18',
      'elk.spacing.edgeNode': '24',
      'elk.layered.layering.strategy': isDiff ? 'INTERACTIVE' : 'NETWORK_SIMPLEX',
      'elk.layered.nodePlacement.strategy': isDiff ? 'BRANDES_KOEPF' : 'NETWORK_SIMPLEX',
      'elk.layered.nodePlacement.favorStraightEdges': 'true',
      'org.eclipse.elk.layered.nodePlacement.bk.edgeStraightening': 'IMPROVE_STRAIGHTNESS',
      'org.eclipse.elk.layered.crossingMinimization.semiInteractive': isDiff ? 'true' : 'false',
      'partitioning.activate': 'false',
      'org.eclipse.elk.partitioning.activate': 'false',
    },
    children: elkChildren,
    edges: elkEdges,
  }

  let layoutResult: any
  try {
    layoutResult = await elk.layout(elkGraph)
  } catch (err: any) {
    console.warn('[elkTopologyLayout] ELK layout failed, fallback to empty layout:', err)
    return fallback
  }

  // 5. 將 ELK 幾何輸出映射為 UniversalTopologyLayout 結構
  const layoutNodes: LayoutNode[] = []
  const junctionDots: JunctionDot[] = []
  const nodePositionLookup = new Map<string, LayoutNode>()
  const busNodeLookup = new Map<string, any>()

  for (const child of layoutResult.children || []) {
    // 5A. 虛擬 Junction 節點提取為電氣焊點圓點 (不納入可見元件卡片 layoutNodes)
    if (child.id.startsWith('junc_') || child.id.startsWith('merge_junc_')) {
      const pol = juncPolarityMap.get(child.id) || 'p'
      junctionDots.push({
        id: child.id,
        x: Math.round(child.x + child.width / 2),
        y: Math.round(child.y + child.height / 2),
        polarity: pol,
      })
      continue
    }

    if (child.id.startsWith('diff_bus_')) {
      busNodeLookup.set(child.id, child)
      continue
    }

    const rawNode = data.nodes.find((n) => n.id === child.id)
    if (!rawNode) continue

    const isSingleTp = isTestPointNode(rawNode) && rawNode.pins.length === 1
    const lPorts: LayoutPort[] = []

    for (const p of child.ports || []) {
      const pinNum = p.id.replace(`${child.id}_`, '')
      const rawPin = rawNode.pins.find((pin) => pin.pin_number === pinNum)
      const orientation =
        p.layoutOptions?.['elk.port.side'] === 'WEST'
          ? 'left'
          : p.layoutOptions?.['elk.port.side'] === 'EAST'
            ? 'right'
            : p.layoutOptions?.['elk.port.side'] === 'NORTH'
              ? 'top'
              : 'bottom'

      const relX = Math.abs(p.x) < 0.001 ? 0 : Math.round(p.x)
      const relY = Math.round(p.y)
      lPorts.push({
        id: p.id,
        pinNumber: pinNum,
        pinName: rawPin?.pin_name,
        orientation,
        x: Math.round(child.x + relX),
        y: Math.round(child.y + relY),
        relX,
        relY,
        polarity: getPinPol(rawNode.id, rawPin || { pin_number: pinNum }, 0),
      })
    }

    const tpPol = rawNode.pins[0] ? getPinPol(rawNode.id, rawNode.pins[0], 0) : 'p'
    const lNode: LayoutNode = {
      id: rawNode.id,
      refDes: rawNode.ref_des,
      category: rawNode.category,
      role: rawNode.role,
      partNumber: rawNode.part_number,
      value: rawNode.value,
      x: child.x,
      y: child.y,
      width: child.width,
      height: child.height,
      ports: lPorts,
      isMounted: rawNode.is_mounted !== false && rawNode.isMounted !== false,
      bom: rawNode.bom,
      partdbMissing: rawNode.partdb_missing === true,
      isTestPoint: isTestPointNode(rawNode),
      isSinglePin: isSingleTp,
      tpDirection: rawNode.lane === 'tap' || isSingleTp ? (tpPol === 'p' ? 'up' : 'down') : undefined,
    }

    layoutNodes.push(lNode)
    nodePositionLookup.set(lNode.id, lNode)
  }

  // 5B. 建立 diff_bus 幾何吸附點與電氣焊點 (Junction Dots)
  // 依據通用層級分層邏輯，將差分分流焊點錨定在下一級主幹串聯電阻/目標元件引腳前方 36px，
  // 並確保分支折線 100% 自焊點中心垂直引出，絕無空白漂浮
  interface BusSnap {
    snapX_p: number
    snapY_p: number
    snapX_n: number
    snapY_n: number
  }
  const busSnapMap = new Map<string, BusSnap>()

  for (const [busId, busChild] of busNodeLookup.entries()) {
    const srcNodeId = busId.replace('diff_bus_', '')
    const conns = connsBySource.get(srcNodeId) || []
    const pConns = conns.filter((c) => resolvePolarity(c.rail_id, c.net_name) === 'p')
    const nConns = conns.filter((c) => resolvePolarity(c.rail_id, c.net_name) === 'n')
    const pMainConn = pConns.find((c) => !c.is_branch) || pConns[0]
    const nMainConn = nConns.find((c) => !c.is_branch) || nConns[0]

    const nextPNode = pMainConn ? nodePositionLookup.get(pMainConn.to_node) : undefined
    const nextNNode = nMainConn ? nodePositionLookup.get(nMainConn.to_node) : undefined
    const srcLNode = nodePositionLookup.get(srcNodeId)

    // 焊點 X 座標：緊鄰下一級主幹串聯電阻/受線元件引腳前方 36px
    let baseSnapX: number
    const targetCandidateX = Math.min(
      nextPNode ? nextPNode.x : Infinity,
      nextNNode ? nextNNode.x : Infinity
    )

    if (targetCandidateX !== Infinity) {
      baseSnapX = targetCandidateX - 36
      if (srcLNode) {
        baseSnapX = Math.max(baseSnapX, srcLNode.x + srcLNode.width + 12)
      }
    } else {
      baseSnapX = Math.round(busChild.x)
    }

    // N 軌靠左 (baseSnapX - 4)，P 軌靠右 (baseSnapX)，維持差分雙軌平行引出絕不交叉
    const snapX_p = baseSnapX
    const snapX_n = baseSnapX - 4

    const relY_p = Math.round(busChild.height >= 90 ? 20 : busChild.height * 0.28)
    const relY_n = Math.round(busChild.height >= 90 ? 90 : busChild.height * 0.72)
    const snapY_p = Math.round(busChild.y + relY_p)
    const snapY_n = Math.round(busChild.y + relY_n)

    busSnapMap.set(busId, { snapX_p, snapY_p, snapX_n, snapY_n })

    // 僅在該軌道有分流時生成電氣焊點
    if (pConns.length > 1) {
      junctionDots.push({
        id: `dot_${busId}_p`,
        x: snapX_p,
        y: snapY_p,
        polarity: 'p',
      })
    }
    if (nConns.length > 1) {
      junctionDots.push({
        id: `dot_${busId}_n`,
        x: snapX_n,
        y: snapY_n,
        polarity: 'n',
      })
    }
  }

  // 6. 後處理 Edges 導線折點圓角化 (Fillet) 與 Net Name 水平段正上方錨定
  const layoutEdges: LayoutEdge[] = []
  const netLabels: NetLabel[] = []

  for (const elkEdge of layoutResult.edges || []) {
    const meta = edgeMetaMap.get(elkEdge.id)
    if (!meta) continue

    const section = elkEdge.sections?.[0]
    if (!section) continue

    let rawPoints: Point[] = [
      section.startPoint,
      ...(section.bendPoints || []),
      section.endPoint,
    ]

    // 幾何分岔吸附 (Branch Snapping)：
    // 若邊連接至 diff_bus 或自 diff_bus 引出，精確校準起訖點與分岔焊點完全重疊，
    // 消除虛擬 Bus 節點寬高所致的視覺中斷，實現主幹直線貫穿、分支自焊點垂直引出
    if (meta.targetId.startsWith('diff_bus_')) {
      const snap = busSnapMap.get(meta.targetId)
      if (snap) {
        const snapX = meta.polarity === 'p' ? snap.snapX_p : snap.snapX_n
        const snapY = meta.polarity === 'p' ? snap.snapY_p : snap.snapY_n
        const startPt = rawPoints[0]
        if (Math.abs(startPt.y - snapY) <= 2) {
          rawPoints = [
            { x: startPt.x, y: snapY },
            { x: snapX, y: snapY },
          ]
        } else {
          rawPoints[rawPoints.length - 1] = { x: snapX, y: snapY }
        }
      }
    } else if (meta.sourceId.startsWith('diff_bus_')) {
      const snap = busSnapMap.get(meta.sourceId)
      if (snap) {
        const snapX = meta.polarity === 'p' ? snap.snapX_p : snap.snapX_n
        const snapY = meta.polarity === 'p' ? snap.snapY_p : snap.snapY_n
        if (meta.isBranch) {
          // 分支線：自焊點 (snapX, snapY) 直接垂直引出至目標高度，再水平連接目標
          // 徹底杜絕向左/向右偏移導致的焊點與折線錯位
          const endPoint = rawPoints[rawPoints.length - 1]
          rawPoints = [
            { x: snapX, y: snapY },
            { x: snapX, y: endPoint.y },
            { x: endPoint.x, y: endPoint.y },
          ]
        } else {
          const endPoint = rawPoints[rawPoints.length - 1]
          if (Math.abs(endPoint.y - snapY) <= 2) {
            rawPoints = [
              { x: snapX, y: snapY },
              { x: endPoint.x, y: snapY },
            ]
          } else {
            rawPoints[0] = { x: snapX, y: snapY }
          }
        }
      }
    }

    // 轉為純 90 度直角正交曼哈頓折線 (移除圓角弧線，符合標準電路拓撲)
    const pathD = pointsToOrthogonalPath(rawPoints)

    layoutEdges.push({
      id: elkEdge.id,
      netName: meta.netName || '',
      railId: meta.railId || '',
      sourceId: meta.sourceId,
      targetId: meta.targetId,
      start: rawPoints[0],
      end: rawPoints[rawPoints.length - 1],
      pathD,
      isBranch: meta.isBranch,
      polarity: meta.polarity,
      isTestPointStub: meta.isTestPointStub,
    })

    // 擷取並微調 Net Name 文字標籤：幾何置中錨定於最長水平導線段正上方 4px
    if (meta.netName && !meta.isBranch && !meta.isTestPointStub) {
      // 尋找此曼哈頓折線中最長之水平導線段
      let bestSegment: { p1: Point; p2: Point; length: number; y: number } | null = null
      for (let i = 0; i < rawPoints.length - 1; i++) {
        const p1 = rawPoints[i]
        const p2 = rawPoints[i + 1]
        if (Math.abs(p1.y - p2.y) < 1.0) {
          const len = Math.abs(p2.x - p1.x)
          if (!bestSegment || len > bestSegment.length) {
            bestSegment = { p1, p2, length: len, y: (p1.y + p2.y) / 2 }
          }
        }
      }

      if (bestSegment && bestSegment.length >= 20) {
        const minX = Math.min(bestSegment.p1.x, bestSegment.p2.x)
        const maxX = Math.max(bestSegment.p1.x, bestSegment.p2.x)
        const targetX = Math.round((minX + maxX) / 2)
        const targetY = Math.round(bestSegment.y - 4)
        const lblWidth = Math.ceil(meta.netName.length * 5.3)

        // 避免同一位置重複標籤
        const isDuplicate = netLabels.some(
          (l) => l.net === meta.netName && Math.abs(l.x - targetX) < 10 && Math.abs(l.y - targetY) < 10
        )
        if (!isDuplicate) {
          netLabels.push({
            id: `lbl_${elkEdge.id}`,
            net: meta.netName,
            x: targetX,
            y: targetY,
            width: lblWidth,
            height: 10,
            polarity: meta.polarity,
          })
        }
      }
    }
  }

  // 7. 電氣電源/接地符號 (VCC / GND) 生成
  const symbols: ElectricalSymbol[] = []
  for (const node of data.nodes) {
    const lNode = nodePositionLookup.get(node.id)
    if (!lNode) continue
    if (node.role === 'pull_up') {
      symbols.push({
        id: `vcc_${node.id}`,
        type: 'vcc',
        label: node.pins.find((p) => p.orientation === 'top')?.pin_name || '+3.3V',
        x: lNode.x + lNode.width / 2,
        y: lNode.y - 10,
      })
    } else if (node.role === 'shunt_ground' || node.role === 'pull_down') {
      symbols.push({
        id: `gnd_${node.id}`,
        type: 'gnd',
        label: 'GND',
        x: lNode.x + lNode.width / 2,
        y: lNode.y + lNode.height + 10,
      })
    }
  }

  // 8. 計算整體 SVG 畫布尺寸
  let maxX = 300
  let maxY = isDiff ? 220 : 140
  for (const n of layoutNodes) {
    if (n.x + n.width > maxX) maxX = n.x + n.width
    if (n.y + n.height > maxY) maxY = n.y + n.height
  }
  for (const e of layoutEdges) {
    if (e.end.x > maxX) maxX = e.end.x
    if (e.end.y > maxY) maxY = e.end.y
  }

  return {
    width: Math.round(maxX + 48),
    height: Math.round(Math.max(maxY + 36, isDiff ? 240 : 140)),
    title,
    channelType,
    nodes: layoutNodes,
    edges: layoutEdges,
    junctionDots,
    netLabels,
    symbols,
  }
}
