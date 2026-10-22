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
  type UniversalConnection,
  estimateNodeSize,
  isTestPointNode,
  resolvePolarity,
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
 * 將點序列轉換為帶 4px 平滑微圓角 (Fillet) 的 SVG 曼哈頓折線 Path D
 *
 * @param {Point[]} points - 折點陣列 (含起點、轉折點與終點)
 * @param {number} radius - 轉角微圓角半徑 (預設 4px)
 * @returns {string} SVG Path d 字串
 */
export function pointsToSmoothOrthogonalPath(points: Point[], radius: number = 4): string {
  if (points.length === 0) return ''
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`
  if (points.length === 2) {
    return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`
  }

  // 1. 去除重疊或共線冗餘點
  const cleaned: Point[] = [points[0]]
  for (let i = 1; i < points.length; i++) {
    const prev = cleaned[cleaned.length - 1]
    const cur = points[i]
    if (Math.abs(prev.x - cur.x) > 0.5 || Math.abs(prev.y - cur.y) > 0.5) {
      cleaned.push(cur)
    }
  }

  if (cleaned.length <= 2) {
    return `M ${cleaned[0].x} ${cleaned[0].y} L ${cleaned[cleaned.length - 1].x} ${cleaned[cleaned.length - 1].y}`
  }

  const dSegments: string[] = [`M ${cleaned[0].x} ${cleaned[0].y}`]

  for (let i = 1; i < cleaned.length - 1; i++) {
    const prev = cleaned[i - 1]
    const cur = cleaned[i]
    const next = cleaned[i + 1]

    const inLen = Math.hypot(cur.x - prev.x, cur.y - prev.y)
    const outLen = Math.hypot(next.x - cur.x, next.y - cur.y)
    const actualR = Math.min(radius, inLen / 2, outLen / 2)

    if (actualR < 1) {
      dSegments.push(`L ${cur.x} ${cur.y}`)
      continue
    }

    // 計算轉折前入點與轉折後出點
    const inDx = (cur.x - prev.x) / inLen
    const inDy = (cur.y - prev.y) / inLen
    const outDx = (next.x - cur.x) / outLen
    const outDy = (next.y - cur.y) / outLen

    const pStart = {
      x: Math.round((cur.x - inDx * actualR) * 10) / 10,
      y: Math.round((cur.y - inDy * actualR) * 10) / 10,
    }
    const pEnd = {
      x: Math.round((cur.x + outDx * actualR) * 10) / 10,
      y: Math.round((cur.y + outDy * actualR) * 10) / 10,
    }

    dSegments.push(`L ${pStart.x} ${pStart.y}`)
    dSegments.push(`Q ${cur.x} ${cur.y} ${pEnd.x} ${pEnd.y}`)
  }

  const last = cleaned[cleaned.length - 1]
  dSegments.push(`L ${last.x} ${last.y}`)

  return dSegments.join(' ')
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

  // 2. 構建 ELK 節點與引腳 (全量圖論化：主元件、被動元件、VCC、GND、測試點全數納入)
  const elkChildren: any[] = []
  const nodeRoleMap = new Map<string, string>()

  for (const node of data.nodes) {
    const isSingleTp = isTestPointNode(node) && node.pins.length === 1
    const { width, height } = estimateNodeSize(node, isSingleTp)
    nodeRoleMap.set(node.id, node.role)

    // 設定引腳相對座標與方位 (WEST=入端, EAST=出端, NORTH=頂部, SOUTH=底部)
    const elkPorts: any[] = []
    const isTerminal = node.role === 'terminal'
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
      // 差分端點 IC / Connector
      const pPins = node.pins.filter((p, i) => getPinPol(node.id, p, i) === 'p')
      const nPins = node.pins.filter((p, i) => getPinPol(node.id, p, i) === 'n')
      const isSrc = data.connections.some((c) => c.from_node === node.id)
      const portSide = isSrc ? 'EAST' : 'WEST'
      const portRelX = isSrc ? width : 0

      pPins.forEach((pin, pIdx) => {
        const relY = Math.round(height * 0.28 + pIdx * 16)
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
        const relY = Math.round(height * 0.72 + nIdx * 16)
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
      // 4-pin CMC 共模扼流圈
      node.pins.forEach((p, idx) => {
        const isLeft = p.orientation === 'left' || idx === 0 || idx === 2
        const pol = getPinPol(node.id, p, idx)
        const relX = isLeft ? 0 : width
        const relY = pol === 'p' ? Math.round(height * 0.28) : Math.round(height * 0.72)
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

    // 差分對稱分區約束：正極設 partition 0、負極設 partition 1
    const firstPinPol = node.pins[0] ? getPinPol(node.id, node.pins[0], 0) : 'p'
    const partitionVal = isDiff && !isTerminal && node.pins.length <= 2 ? (firstPinPol === 'p' ? '0' : '1') : '0'

    elkChildren.push({
      id: node.id,
      width,
      height,
      ports: elkPorts,
      layoutOptions: {
        'elk.portConstraints': 'FIXED_POS',
        'elk.priority': nodePriority,
        'elk.partition': partitionVal,
      },
    })
  }

  // 3. 純前端圖改寫器 (Graph Rewriter)：偵測 1-to-N 匯流分流，注入 4x4 Dummy Junction 虛擬節點
  // 依據出發點 (from_node#from_pin) 分組
  const sourceGroups = new Map<string, UniversalConnection[]>()
  for (const conn of data.connections) {
    const key = `${conn.from_node}#${conn.from_pin}`
    if (!sourceGroups.has(key)) sourceGroups.set(key, [])
    sourceGroups.get(key)!.push(conn)
  }

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

  for (const conns of sourceGroups.values()) {
    const firstConn = conns[0]
    const srcNode = data.nodes.find((n) => n.id === firstConn.from_node)
    if (!srcNode) continue

    const pol = resolvePolarity(firstConn.rail_id, firstConn.net_name)
    const partitionVal = isDiff ? (pol === 'p' ? '0' : '1') : '0'

    if (conns.length > 1) {
      // 1-to-N 分流：建立 Dummy Junction 虛擬節點 (對齊 netlistsvg 標準作法)
      const juncId = `junc_${firstConn.from_node}_${firstConn.from_pin}`
      juncPolarityMap.set(juncId, pol)

      // 4x4 Dummy Junction 節點，配置 WEST 入埠、EAST 出埠與 NORTH/SOUTH 分支引出埠
      elkChildren.push({
        id: juncId,
        width: 4,
        height: 4,
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
            y: pol === 'p' ? 0 : 4,
            layoutOptions: { 'elk.port.side': pol === 'p' ? 'NORTH' : 'SOUTH' },
          },
        ],
        layoutOptions: {
          'elk.portConstraints': 'FIXED_POS',
          'elk.priority': '8', // 與主幹維持同級階層
          'elk.partition': partitionVal,
        },
      })

      // 3A. 入端主邊：Source -> Dummy Junction
      const mainConn = conns.find((c) => !c.is_branch) || conns[0]
      const netName = mainConn.net_name || ''
      const inEdgeId = `edge_${edgeCounter++}`

      const inLabels: any[] = []
      if (netName) {
        const labelWidth = Math.ceil(netName.length * 5.3)
        inLabels.push({
          id: `lbl_${inEdgeId}`,
          text: netName,
          width: labelWidth,
          height: 10,
          layoutOptions: {
            'elk.edgeLabels.placement': 'ABOVE',
            'elk.edgeLabels.inline': 'false',
          },
        })
      }

      elkEdges.push({
        id: inEdgeId,
        sources: [`${firstConn.from_node}_${firstConn.from_pin}`],
        targets: [`${juncId}_in`],
        labels: inLabels,
        layoutOptions: {
          'elk.priority': '8',
        },
      })
      edgeMetaMap.set(inEdgeId, {
        netName,
        railId: mainConn.rail_id,
        sourceId: firstConn.from_node,
        targetId: juncId,
        isBranch: false,
        polarity: pol,
        isTestPointStub: false,
      })

      // 3B. 出端分支邊：Dummy Junction -> Targets (主幹走 EAST，測試點/次軌走 tap)
      conns.forEach((c) => {
        const tgtNode = data.nodes.find((n) => n.id === c.to_node)
        if (!tgtNode) return

        const isSingleTp = isTestPointNode(tgtNode) && tgtNode.pins.length === 1
        const isBranch = Boolean(c.is_branch)
        const outEdgeId = `edge_${edgeCounter++}`

        // 單腳測試點走 tap 埠 (垂直引出)；主幹走 out 埠 (水平向右)
        const srcPortId = isSingleTp ? `${juncId}_tap` : `${juncId}_out`
        const tgtPortId = `${c.to_node}_${c.to_pin}`

        const edgeOptions: Record<string, string> = {
          'elk.priority': isSingleTp ? '1' : isBranch ? '3' : '8',
        }
        if (isSingleTp) {
          // 強制最短邊，就近緊湊排列
          edgeOptions['elk.layered.priority.shortness'] = '10'
        }

        elkEdges.push({
          id: outEdgeId,
          sources: [srcPortId],
          targets: [tgtPortId],
          labels: [], // 標籤統一置於入端主邊，避免重疊
          layoutOptions: edgeOptions,
        })
        edgeMetaMap.set(outEdgeId, {
          netName: c.net_name,
          railId: c.rail_id,
          sourceId: juncId,
          targetId: c.to_node,
          isBranch,
          polarity: pol,
          isTestPointStub: isSingleTp,
        })
      })
    } else {
      // 1-to-1 直連無分流：建立直接連線
      const c = firstConn
      const tgtNode = data.nodes.find((n) => n.id === c.to_node)
      if (!tgtNode) continue

      const isSingleTp = isTestPointNode(tgtNode) && tgtNode.pins.length === 1
      const isBranch = Boolean(c.is_branch)
      const netName = c.net_name || ''
      const directEdgeId = `edge_${edgeCounter++}`

      const labels: any[] = []
      if (netName && !isBranch) {
        const labelWidth = Math.ceil(netName.length * 5.3)
        labels.push({
          id: `lbl_${directEdgeId}`,
          text: netName,
          width: labelWidth,
          height: 10,
          layoutOptions: {
            'elk.edgeLabels.placement': 'ABOVE',
            'elk.edgeLabels.inline': 'false',
          },
        })
      }

      const edgeOptions: Record<string, string> = {
        'elk.priority': isSingleTp ? '1' : isBranch ? '3' : '8',
      }
      if (isSingleTp) {
        edgeOptions['elk.layered.priority.shortness'] = '10'
      }

      elkEdges.push({
        id: directEdgeId,
        sources: [`${c.from_node}_${c.from_pin}`],
        targets: [`${c.to_node}_${c.to_pin}`],
        labels,
        layoutOptions: edgeOptions,
      })
      edgeMetaMap.set(directEdgeId, {
        netName,
        railId: c.rail_id,
        sourceId: c.from_node,
        targetId: c.to_node,
        isBranch,
        polarity: pol,
        isTestPointStub: isSingleTp,
      })
    }
  }

  // 依據是否有 Net Name 標籤動態配置層級淨間距：
  // 若邊線上存在 Edge Labels，ELK 內部會自動累加標籤寬度與安全邊距 (Edge Length ≈ Label Width + Margin)，
  // 因此 nodeNodeBetweenLayers 僅需配置適度淨間隙 (24px)，避免重複累加導致間距暴增至 300px；
  // 若完全無標籤，則預留緊湊標準間距 45px。
  const hasLabels = data.connections.some((c) => Boolean(c.net_name && !c.is_branch))
  const layerSpacing = hasLabels ? '24' : '45'

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
      'elk.layered.layering.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.partitioning.activate': isDiff ? 'true' : 'false',
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

  for (const child of layoutResult.children || []) {
    // 5A. 虛擬 Junction 節點提取為電氣焊點圓點 (不納入可見元件卡片 layoutNodes)
    if (child.id.startsWith('junc_')) {
      const pol = juncPolarityMap.get(child.id) || 'p'
      junctionDots.push({
        id: child.id,
        x: Math.round(child.x + child.width / 2),
        y: Math.round(child.y + child.height / 2),
        polarity: pol,
      })
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

  // 6. 後處理 Edges 導線折點圓角化 (Fillet) 與 Net Name 水平段正上方錨定
  const layoutEdges: LayoutEdge[] = []
  const netLabels: NetLabel[] = []

  for (const elkEdge of layoutResult.edges || []) {
    const meta = edgeMetaMap.get(elkEdge.id)
    if (!meta) continue

    const section = elkEdge.sections?.[0]
    if (!section) continue

    const rawPoints: Point[] = [
      section.startPoint,
      ...(section.bendPoints || []),
      section.endPoint,
    ]

    // 平滑化為 4px 微圓角曼哈頓折線
    const pathD = pointsToSmoothOrthogonalPath(rawPoints, 4)

    layoutEdges.push({
      id: elkEdge.id,
      netName: meta.netName || '',
      railId: meta.railId || '',
      sourceId: meta.sourceId,
      targetId: meta.targetId,
      start: section.startPoint,
      end: section.endPoint,
      pathD,
      isBranch: meta.isBranch,
      polarity: meta.polarity,
      isTestPointStub: meta.isTestPointStub,
    })

    // 擷取並微調 Edge Labels：雙重保障錨定於水平線段正上方 4px
    if (elkEdge.labels && elkEdge.labels.length > 0) {
      for (const lbl of elkEdge.labels) {
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

        let targetX = Math.round(lbl.x + lbl.width / 2)
        let targetY = Math.round(lbl.y + lbl.height / 2)

        if (bestSegment && bestSegment.length >= 10) {
          const minX = Math.min(bestSegment.p1.x, bestSegment.p2.x)
          const maxX = Math.max(bestSegment.p1.x, bestSegment.p2.x)
          // 若 ELK 算出的 X 超出水平段可視範圍，則居中置於水平段
          if (targetX < minX + lbl.width / 2 || targetX > maxX - lbl.width / 2) {
            targetX = Math.round((minX + maxX) / 2)
          }
          // 文字 Y 座標錨定在導線上方 4px (SVG baseline 在文字底部，置於 y - 4 永遠不切線)
          targetY = Math.round(bestSegment.y - 4)
        } else if (bestSegment) {
          targetY = Math.round(bestSegment.y - 4)
        }

        netLabels.push({
          id: lbl.id,
          net: lbl.text,
          x: targetX,
          y: targetY,
          width: lbl.width,
          height: lbl.height,
          polarity: meta.polarity,
        })
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
