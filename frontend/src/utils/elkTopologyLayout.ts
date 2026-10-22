/**
 * @file elkTopologyLayout.ts
 * @description 基於 ELKjs (Eclipse Layout Kernel) 的現代化電路拓撲排版引擎 (漸進式 POC 模組)
 * 遵循 2026 前端 EDA 原理圖最佳實踐：
 * 1. 採用動態按需載入 (Dynamic import) elk.bundled.js，首屏零 Bundle 負擔
 * 2. 採用 Layered 階層流向演算法搭配 FIXED_POS 引腳埠約束與 Orthogonal 曼哈頓直角走線
 * 3. 支援全量圖論化 (Full ELK Graph) 建模：主次信號鏈路以 priority 權重區分
 * 4. 支援差分雙軌對稱性、4px 圓角階梯折線平滑化與分支交會焊點 (Junction Dots) 偵測
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
      // 單腳測試點：單埠居中
      const pol = node.pins[0] ? getPinPol(node.id, node.pins[0], 0) : 'p'
      elkPorts.push({
        id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
        width: 4,
        height: 4,
        x: Math.round(width / 2),
        y: pol === 'p' ? height : 0,
        layoutOptions: {
          'elk.port.side': pol === 'p' ? 'SOUTH' : 'NORTH',
        },
      })
    } else if (isPullUp) {
      elkPorts.push({
        id: `${node.id}_2`,
        width: 4,
        height: 4,
        x: Math.round(width / 2),
        y: 0,
        layoutOptions: { 'elk.port.side': 'NORTH' },
      })
      elkPorts.push({
        id: `${node.id}_1`,
        width: 4,
        height: 4,
        x: Math.round(width / 2),
        y: height,
        layoutOptions: { 'elk.port.side': 'SOUTH' },
      })
    } else if (isShunt) {
      elkPorts.push({
        id: `${node.id}_1`,
        width: 4,
        height: 4,
        x: Math.round(width / 2),
        y: 0,
        layoutOptions: { 'elk.port.side': 'NORTH' },
      })
      elkPorts.push({
        id: `${node.id}_2`,
        width: 4,
        height: 4,
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
          width: 4,
          height: 4,
          x: portRelX,
          y: relY,
          layoutOptions: { 'elk.port.side': portSide },
        })
      })
      nPins.forEach((pin, nIdx) => {
        const relY = Math.round(height * 0.72 + nIdx * 16)
        elkPorts.push({
          id: `${node.id}_${pin.pin_number}`,
          width: 4,
          height: 4,
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
          width: 4,
          height: 4,
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
          width: 4,
          height: 4,
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
    else if (isPullUp || isShunt || isSingleTp) nodePriority = '2'

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

  // 3. 構建 ELK 連線 (Edges) 與原生文字標籤 (Edge Labels)
  const elkEdges: any[] = []
  data.connections.forEach((conn, cIdx) => {
    const srcNode = data.nodes.find((n) => n.id === conn.from_node)
    const tgtNode = data.nodes.find((n) => n.id === conn.to_node)
    if (!srcNode || !tgtNode) return

    const srcPortId = `${conn.from_node}_${conn.from_pin}`
    const tgtPortId = `${conn.to_node}_${conn.to_pin}`

    // 依據主幹/並聯分支賦予 edge priority 權重
    const edgePriority = conn.is_branch ? '3' : '8'
    const netName = conn.net_name || ''
    const labelWidth = Math.ceil(netName.length * 5.3)

    const labels: any[] = []
    if (netName && !conn.is_branch) {
      labels.push({
        id: `lbl_${cIdx}_${netName}`,
        text: netName,
        width: labelWidth,
        height: 10,
        layoutOptions: {
          'elk.edgeLabels.placement': 'CENTER',
        },
      })
    }

    elkEdges.push({
      id: `edge_${cIdx}`,
      sources: [srcPortId],
      targets: [tgtPortId],
      labels,
      layoutOptions: {
        'elk.priority': edgePriority,
      },
    })
  })

  // 4. 執行 ELKjs 全量圖論排版
  const elkGraph = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.edgeRouting': 'ORTHOGONAL',
      'elk.layered.spacing.nodeNodeBetweenLayers': '65',
      'elk.spacing.nodeNode': '36',
      'elk.spacing.edgeEdge': '18',
      'elk.spacing.edgeNode': '24',
      'elk.partitioning.activate': isDiff ? 'true' : 'false',
    },
    children: elkChildren,
    edges: elkEdges,
  }

  let layoutResult: any
  try {
    layoutResult = await elk.layout(elkGraph)
  } catch (err) {
    console.warn('[elkTopologyLayout] ELK layout failed, fallback to empty layout:', err)
    return fallback
  }

  // 5. 將 ELK 幾何輸出映射為 UniversalTopologyLayout 結構
  const layoutNodes: LayoutNode[] = []
  const nodePositionLookup = new Map<string, LayoutNode>()

  for (const child of layoutResult.children || []) {
    const rawNode = data.nodes.find((n) => n.id === child.id)
    if (!rawNode) continue

    const isSingleTp = isTestPointNode(rawNode) && rawNode.pins.length === 1
    const lPorts: LayoutPort[] = []

    for (const p of child.ports || []) {
      const pinNum = p.id.replace(`${child.id}_`, '')
      const rawPin = rawNode.pins.find((pin) => pin.pin_number === pinNum)
      const orientation = p.layoutOptions?.['elk.port.side'] === 'WEST'
        ? 'left'
        : p.layoutOptions?.['elk.port.side'] === 'EAST'
          ? 'right'
          : p.layoutOptions?.['elk.port.side'] === 'NORTH'
            ? 'top'
            : 'bottom'

      lPorts.push({
        id: p.id,
        pinNumber: pinNum,
        pinName: rawPin?.pin_name,
        orientation,
        x: child.x + p.x,
        y: child.y + p.y,
        relX: p.x,
        relY: p.y,
        polarity: getPinPol(rawNode.id, rawPin || { pin_number: pinNum }, 0),
      })
    }

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
      tpDirection: rawNode.lane === 'tap' || isSingleTp ? 'up' : undefined,
    }

    layoutNodes.push(lNode)
    nodePositionLookup.set(lNode.id, lNode)
  }

  // 6. 後處理 Edges 導線折點圓角化 (Fillet) 與分支交會焊點 (Junction Dots) 識別
  const layoutEdges: LayoutEdge[] = []
  const junctionDots: JunctionDot[] = []
  const netLabels: NetLabel[] = []
  const branchStartPoints: Point[] = []

  for (const elkEdge of layoutResult.edges || []) {
    const cIdx = Number(elkEdge.id.replace('edge_', ''))
    const conn = data.connections[cIdx]
    if (!conn) continue

    const polarity = resolvePolarity(conn.rail_id, conn.net_name)
    const section = elkEdge.sections?.[0]
    if (!section) continue

    const rawPoints: Point[] = [
      section.startPoint,
      ...(section.bendPoints || []),
      section.endPoint,
    ]

    // 平滑化為 4px 微圓角曼哈頓折線
    const pathD = pointsToSmoothOrthogonalPath(rawPoints, 4)

    if (conn.is_branch) {
      branchStartPoints.push({ x: section.startPoint.x, y: section.startPoint.y })
    }

    layoutEdges.push({
      id: elkEdge.id,
      netName: conn.net_name,
      railId: conn.rail_id,
      sourceId: conn.from_node,
      targetId: conn.to_node,
      start: section.startPoint,
      end: section.endPoint,
      pathD,
      isBranch: Boolean(conn.is_branch),
      polarity,
      isTestPointStub: isTestPointNode(data.nodes.find((n) => n.id === conn.to_node) || ({} as any)),
    })

    // 擷取 ELK 原生算出的 Edge Labels
    if (elkEdge.labels && elkEdge.labels.length > 0) {
      for (const lbl of elkEdge.labels) {
        netLabels.push({
          id: lbl.id,
          net: lbl.text,
          x: Math.round(lbl.x + lbl.width / 2),
          y: Math.round(lbl.y + lbl.height / 2),
          width: lbl.width,
          height: lbl.height,
          polarity,
        })
      }
    }
  }

  // 7. 分支匯流電氣焊點圓點產生 (僅在分支起點與主幹交會處打點)
  branchStartPoints.forEach((pt, idx) => {
    junctionDots.push({
      id: `elk_junc_${idx}`,
      x: Math.round(pt.x),
      y: Math.round(pt.y),
      polarity: 'p',
    })
  })

  // 8. 電氣電源/接地符號 (VCC / GND) 生成
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

  // 9. 計算整體 SVG 畫布尺寸
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
