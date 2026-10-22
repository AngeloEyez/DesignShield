/**
 * @file universalTopologyHelpers.ts
 * @description 通用電路拓撲排版型別定義、幾何計算與分層路徑帶 (Layered DAG + Path Bands) 輔助函式模組
 */

export interface UniversalPin {
  pin_number: string
  pin_name?: string
  orientation?: 'left' | 'right' | 'top' | 'bottom'
}

export interface UniversalNode {
  id: string
  ref_des: string
  category: string
  sub_category?: string
  role: 'terminal' | 'series' | 'pull_up' | 'pull_down' | 'shunt_ground' | 'bridge' | string
  part_number?: string
  value?: string
  pins: UniversalPin[]
  is_mounted?: boolean
  isMounted?: boolean
  bom?: string
  /** 版面提示：branch=並聯分支穿透元件 (繪於次要路徑帶)，tap=中途分接端點或測試點 */
  lane?: 'branch' | 'tap' | string
  /** 該元件查無 PartDB (僅顯示用虛線方塊，不參與導通判定) */
  partdb_missing?: boolean
  /** 是否為測試點元件 (如 TP56, CTP20) */
  is_test_point?: boolean
}

export interface UniversalConnection {
  net_name: string
  rail_id: string
  from_node: string
  from_pin: string
  to_node: string
  to_pin: string
  is_branch?: boolean
}

export interface UniversalRail {
  id: string
  name: string
  polarity?: 'P' | 'N' | null
}

export interface UniversalTopologyData {
  title: string
  channel_type: 'single' | 'differential' | 'bus' | string
  rails: UniversalRail[]
  nodes: UniversalNode[]
  connections: UniversalConnection[]
  metadata?: Record<string, any>
}

export interface Point {
  x: number
  y: number
}

export interface LayoutPort {
  id: string
  pinNumber: string
  pinName?: string
  orientation: 'left' | 'right' | 'top' | 'bottom'
  x: number
  y: number
  relX: number
  relY: number
  polarity?: 'p' | 'n'
}

export interface LayoutNode {
  id: string
  refDes: string
  category: string
  role: string
  partNumber?: string
  value?: string
  x: number
  y: number
  width: number
  height: number
  ports: LayoutPort[]
  isMounted?: boolean
  bom?: string
  partdbMissing?: boolean
  /** 是否為測試點元件 */
  isTestPoint?: boolean
  /** 是否為單引腳緊湊元件 (不顯示引腳號碼與名稱) */
  isSinglePin?: boolean
  /** 單引腳測試點引出方向 ('up' | 'down') */
  tpDirection?: 'up' | 'down'
}

export interface LayoutEdge {
  id: string
  netName: string
  railId: string
  sourceId: string
  targetId: string
  start: Point
  end: Point
  pathD: string
  isBranch: boolean
  polarity?: 'p' | 'n'
  /** 是否為單腳測試點引出短線 (採用灰色繪製) */
  isTestPointStub?: boolean
}

export interface JunctionDot {
  id: string
  x: number
  y: number
  polarity?: 'p' | 'n'
}

export interface NetLabel {
  id: string
  net: string
  x: number
  y: number
  width: number
  height: number
  polarity?: 'p' | 'n'
}

export interface ElectricalSymbol {
  id: string
  type: 'vcc' | 'gnd'
  label: string
  x: number
  y: number
}

export interface UniversalTopologyLayout {
  width: number
  height: number
  title: string
  channelType: string
  nodes: LayoutNode[]
  edges: LayoutEdge[]
  junctionDots: JunctionDot[]
  netLabels: NetLabel[]
  symbols: ElectricalSymbol[]
}

/**
 * 雙軌邏輯單元 (Logical Unit)：
 * 在差分通道中，將同一 Stage Column 與同一水平路徑帶 (Band) 內的元件封裝為單一排版單元
 * （可為單一跨軌元件如 Terminal / 4-pin CMC / 中繼 IC，或成對的 P/N 2-pin 串聯被動元件）。
 */
export interface LogicalUnit {
  id: string
  col: number
  band: number
  dualNode?: UniversalNode
  pNode?: UniversalNode
  nNode?: UniversalNode
  nodeIds: string[]
  isMounted: boolean
  isBranchHint: boolean
  isTapHint: boolean
  isTerminal: boolean
  orderIdx: number
}

/**
 * 水平導線幾何區段紀錄 (供 Net Name 標籤直接錨定與單腳測試點掛載使用)
 */
export interface HorizontalSegmentRecord {
  netName: string
  polarity: 'p' | 'n'
  band: number
  colStart: number
  colEnd: number
  x1: number
  x2: number
  y: number
  isMainBand: boolean
}

/**
 * 曼哈頓直角階梯折線產生器 (含半徑 4px 微圓角)
 *
 * @param {Point} start - 起點座標
 * @param {Point} end - 終點座標
 * @param {number} radius - 轉角圓弧半徑 (預設 4px)
 * @param {number} bendX - 指定垂直轉折 X 座標
 * @returns {string} SVG Path d 字串
 */
export function generateOrthogonalPath(
  start: Point,
  end: Point,
  radius: number = 4,
  bendX?: number
): string {
  const dx = end.x - start.x
  const dy = end.y - start.y

  if (Math.abs(dy) < 1) {
    return `M ${start.x} ${start.y} L ${end.x} ${end.y}`
  }

  const midX = bendX !== undefined ? bendX : start.x + dx / 2
  const r = Math.min(radius, Math.abs(dx) / 2, Math.abs(dy) / 2)

  const dirY = dy > 0 ? 1 : -1
  const dirX = dx >= 0 ? 1 : -1

  if (dirX >= 0) {
    return [
      `M ${start.x} ${start.y}`,
      `L ${midX - r} ${start.y}`,
      `Q ${midX} ${start.y} ${midX} ${start.y + dirY * r}`,
      `L ${midX} ${end.y - dirY * r}`,
      `Q ${midX} ${end.y} ${midX + r} ${end.y}`,
      `L ${end.x} ${end.y}`,
    ].join(' ')
  } else {
    return [
      `M ${start.x} ${start.y}`,
      `L ${midX + r} ${start.y}`,
      `Q ${midX} ${start.y} ${midX} ${start.y + dirY * r}`,
      `L ${midX} ${end.y - dirY * r}`,
      `Q ${midX} ${end.y} ${midX - r} ${end.y}`,
      `L ${end.x} ${end.y}`,
    ].join(' ')
  }
}

/**
 * 判定節點是否為測試點 (TestPoint，嚴格依據 Level 1 sub_category 或後端 is_test_point 旗標)
 *
 * @param {UniversalNode} node - 待判定之通用節點
 * @returns {boolean} 是否為測試點
 */
export function isTestPointNode(node: UniversalNode): boolean {
  if (node.is_test_point === true) return true
  const sub = (node.sub_category || '').toLowerCase().replace(/_/g, '')
  if (sub === 'testpoint') return true
  const cat = (node.category || '').toLowerCase().replace(/_/g, '')
  if (cat === 'testpoint') return true
  return false
}

/**
 * 判定節點是否為跨正負雙軌之元件 (Terminal 端點、4-pin CMC 共模扼流圈、或 4-pin 中繼 IC)
 *
 * @param {UniversalNode} node - 待判定之通用節點
 * @returns {boolean} 是否為雙軌元件
 */
export function isDualRailComponent(node: UniversalNode): boolean {
  if (node.role === 'terminal') return true
  if (node.pins.length >= 4) return true
  const cat = (node.category || '').toLowerCase()
  return cat.includes('choke') || cat.includes('ic')
}

/**
 * 估算節點寬度與高度 (含雙側具名引腳之中繼 IC 自動寬度擴展與單腳測試點緊湊尺寸)
 *
 * @param {UniversalNode} node - 待估算之通用節點
 * @param {boolean} isCompactTp - 是否作為緊湊型單腳測試點渲染
 * @returns {{ width: number; height: number }} 節點寬高像素值
 */
export function estimateNodeSize(
  node: UniversalNode,
  isCompactTp: boolean = false
): { width: number; height: number } {
  if (isCompactTp || (isTestPointNode(node) && node.pins.length === 1)) {
    const tpWidth = Math.max(34, (node.ref_des?.length || 4) * 6 + 10)
    return { width: Math.round(tpWidth), height: 28 }
  }

  const isTerminal = node.role === 'terminal'
  const isPassive =
    node.role === 'series' ||
    node.role === 'pull_up' ||
    node.role === 'shunt_ground' ||
    node.role === 'pull_down'

  const refDesLen = node.ref_des.length
  let maxPinTextLen = 0
  let maxLeftPinLen = 0
  let maxRightPinLen = 0
  let hasNamedPin = false

  for (const p of node.pins) {
    const hasDistinctName = Boolean(p.pin_name && p.pin_name !== p.pin_number)
    if (hasDistinctName) hasNamedPin = true
    const textLen = (p.pin_number?.length || 0) + (hasDistinctName ? p.pin_name!.length + 2 : 0)
    if (textLen > maxPinTextLen) maxPinTextLen = textLen
    if (p.orientation === 'left') {
      if (textLen > maxLeftPinLen) maxLeftPinLen = textLen
    } else if (p.orientation === 'right') {
      if (textLen > maxRightPinLen) maxRightPinLen = textLen
    }
  }

  let width = 60
  const isIc = (node.category || '').toLowerCase() === 'ic' || (node.pins.length >= 4 && node.role !== 'pull_up' && node.role !== 'shunt_ground')
  if (isTerminal) {
    width = Math.max(76, refDesLen * 9 + 20, maxPinTextLen * 5.6 + 24)
  } else if (isPassive) {
    const valLen = node.value ? node.value.length * 6 : 0
    // 若為中繼 IC (如 KU100) 左右兩側皆有具名引腳，確保寬度足以同時容納左右引腳文字且中間保留 36px 淨空
    const dualSidePinWidth =
      hasNamedPin && maxLeftPinLen > 0 && maxRightPinLen > 0
        ? Math.ceil((maxLeftPinLen + maxRightPinLen) * 5.6) + 36
        : 0
    width = Math.max(56, refDesLen * 8 + 24, valLen + 16, dualSidePinWidth)
  }

  let height = 38
  if (isTerminal) {
    if (node.pins.length > 1) {
      height = Math.max(52, 28 + (node.pins.length - 1) * 22)
    }
  } else if (isIc) {
    // 緊湊自適應多引腳 IC (如中繼 IC KU100)：高度依單側引腳數計算 = 24px Header + N_side * 24px (2-pin 側為 72px)
    const sidePinCount = Math.max(
      node.pins.filter((p) => p.orientation === 'left' || p.orientation === undefined).length,
      node.pins.filter((p) => p.orientation === 'right').length,
      Math.ceil(node.pins.length / 2)
    )
    height = Math.max(68, 24 + sidePinCount * 24)
  } else if (node.role === 'pull_up' || node.role === 'shunt_ground') {
    height = 36
  }

  return { width: Math.round(width), height: Math.round(height) }
}

/**
 * 判定連線或網路名稱之極性 ('p' | 'n')
 *
 * @param {string} railId - 軌道識別碼 ('p_rail' | 'n_rail')
 * @param {string} netName - 網路名稱
 * @returns {'p' | 'n'} 極性 ('p' 或 'n')
 */
export function resolvePolarity(railId?: string, netName?: string): 'p' | 'n' {
  if (railId === 'n_rail') return 'n'
  if (railId === 'p_rail') return 'p'

  if (netName) {
    const clean = netName.trim()
    if (/(?:_N|_DN|_DM|D-)(?:\b|\d+|_|$)/i.test(clean) || /(?:^|_)N$/i.test(clean)) {
      return 'n'
    }
    if (/(?:_P|_DP|D\+)(?:\b|\d+|_|$)/i.test(clean) || /(?:^|_)P$/i.test(clean)) {
      return 'p'
    }
  }

  return 'p'
}

/**
 * 判斷節點是否為外部連接器 (Connector，優先作為右側主幹終點)
 *
 * @param {UniversalNode} node - 待判定節點
 * @returns {boolean} 是否為連接器
 */
export function isConnectorNode(node: UniversalNode): boolean {
  const ref = (node.ref_des || '').trim().toUpperCase()
  const cat = (node.category || '').toLowerCase()
  if (ref.startsWith('XU')) return false
  return /^(?:J|TJ|P|CN|CON)\d*/.test(ref) || cat.includes('connector')
}

/**
 * 預估某個雙軌邏輯單元在指定 pY/nY 下的頂部與底部邊界 (供計算相鄰 Band 安全間距)
 *
 * @param {LogicalUnit} u - 雙軌邏輯單元
 * @param {number} pY - 正極軌道 Y 座標
 * @param {number} nY - 負極軌道 Y 座標
 * @param {(nodeId: string, pin: UniversalPin, idx: number) => 'p' | 'n'} getPinPolarity - 引腳極性查詢函式
 * @returns {{ top: number; bottom: number }} 頂部與底部 Y 座標
 */
export function getUnitVerticalExtent(
  u: LogicalUnit,
  pY: number,
  nY: number,
  getPinPolarity: (nodeId: string, pin: UniversalPin, idx: number) => 'p' | 'n'
): { top: number; bottom: number } {
  if (u.dualNode) {
    const node = u.dualNode
    if (node.role === 'series') {
      const topPad = 26
      const botPad = 16 + (node.partdb_missing ? 14 : 0)
      return { top: pY - topPad, bottom: nY + botPad }
    } else {
      const pPins = node.pins.filter((p, i) => getPinPolarity(node.id, p, i) === 'p')
      const nPins = node.pins.filter((p, i) => getPinPolarity(node.id, p, i) === 'n')
      const minOffset = pPins.length > 1 ? -((pPins.length - 1) * 16) / 2 : 0
      const maxOffset = nPins.length > 1 ? ((nPins.length - 1) * 16) / 2 : 0
      const topY = Math.round(pY + minOffset - 28)
      const botY = Math.max(topY + 54, Math.round(nY + maxOffset + 16))
      return { top: topY, bottom: botY }
    }
  } else {
    return { top: pY - 26, bottom: nY + 14 }
  }
}

/**
 * 基於網路與節點之 DAG 最長路徑分層演算法 (Stage Column Layering)
 *
 * @param {UniversalNode[]} mainNodes - 參與流向分層的主節點清單
 * @param {UniversalConnection[]} flowConnections - 節點間流向連線清單
 * @returns {{ stages: string[][]; nodeColMap: Map<string, number> }} 分層欄位與節點欄位映射表
 */
export function computeStageColumns(
  mainNodes: UniversalNode[],
  flowConnections: UniversalConnection[]
): { stages: string[][]; nodeColMap: Map<string, number> } {
  const nodeColMap = new Map<string, number>()
  for (const n of mainNodes) {
    nodeColMap.set(n.id, 0)
  }

  const netColMap = new Map<string, number>()
  const maxIterations = mainNodes.length + 2
  for (let iter = 0; iter < maxIterations; iter++) {
    let changed = false
    for (let cIdx = 0; cIdx < flowConnections.length; cIdx++) {
      const c = flowConnections[cIdx]
      const srcCol = nodeColMap.get(c.from_node) || 0
      if (srcCol > mainNodes.length) continue
      const netKey = c.net_name ? `${c.rail_id}#${c.net_name}` : `__anon_${cIdx}`
      const curNetCol = netColMap.get(netKey) ?? -1
      if (srcCol > curNetCol) {
        netColMap.set(netKey, srcCol)
        changed = true
      }
    }
    for (let cIdx = 0; cIdx < flowConnections.length; cIdx++) {
      const c = flowConnections[cIdx]
      const netKey = c.net_name ? `${c.rail_id}#${c.net_name}` : `__anon_${cIdx}`
      const nCol = netColMap.get(netKey) ?? (nodeColMap.get(c.from_node) || 0)
      const desiredTgtCol = Math.min(mainNodes.length, nCol + 1)
      const curTgtCol = nodeColMap.get(c.to_node) || 0
      if (desiredTgtCol > curTgtCol) {
        nodeColMap.set(c.to_node, desiredTgtCol)
        changed = true
      }
    }
    if (!changed) break
  }

  // === 反向 ALAP 匯流前置對齊 (ALAP Merge Alignment) ===
  // 1. 對於匯入同一匯流節點 (入度 >= 2) 的所有前置元件 (如 KR135/136 與 KR129/130 匯入 UR800/801)，
  //    強制推齊至同一 Stage Column，消除多路徑長度不等導致的錯位與長跨線。
  // 2. 對於連往相同終端 Connector 的並聯受線元件 (如 UR800/801 與 CMC UL800 連往 J80)，
  //    強制對齊在相同 Stage Column，確保可選/濾波元件與主路徑元件同欄。
  const incomingByTarget = new Map<string, Set<string>>()
  for (const c of flowConnections) {
    if (!incomingByTarget.has(c.to_node)) incomingByTarget.set(c.to_node, new Set())
    incomingByTarget.get(c.to_node)!.add(c.from_node)
  }

  let alapChanged = true
  let alapLoop = 0
  const maxAlapIterations = mainNodes.length + 2
  while (alapChanged && alapLoop < maxAlapIterations) {
    alapChanged = false
    alapLoop++

    // A. 匯流節點的前置節點反向拉齊
    for (const [, predSet] of incomingByTarget.entries()) {
      if (predSet.size > 1) {
        let maxPredCol = 0
        for (const pid of predSet) {
          const pCol = nodeColMap.get(pid) || 0
          if (pCol > maxPredCol) maxPredCol = pCol
        }
        for (const pid of predSet) {
          const curCol = nodeColMap.get(pid) || 0
          if (curCol < maxPredCol) {
            const pPreds = incomingByTarget.get(pid)
            let maxPpredCol = -1
            if (pPreds) {
              for (const ppid of pPreds) {
                const ppCol = nodeColMap.get(ppid) || 0
                if (ppCol > maxPpredCol) maxPpredCol = ppCol
              }
            }
            if (maxPredCol > maxPpredCol) {
              nodeColMap.set(pid, maxPredCol)
              alapChanged = true
            }
          }
        }
      }
    }

    // B. 連往終端 Terminal / Connector 的並聯元件同欄對齊
    const terminalNodes = new Set(
      mainNodes
        .filter(
          (n) =>
            n.role === 'terminal' ||
            ((incomingByTarget.get(n.id)?.size || 0) > 0 &&
              !flowConnections.some((c) => c.from_node === n.id))
        )
        .map((n) => n.id)
    )
    for (const termId of terminalNodes) {
      const preds = incomingByTarget.get(termId)
      if (preds && preds.size > 1) {
        let maxPredCol = 0
        for (const pid of preds) {
          const pCol = nodeColMap.get(pid) || 0
          if (pCol > maxPredCol) maxPredCol = pCol
        }
        for (const pid of preds) {
          const curCol = nodeColMap.get(pid) || 0
          if (curCol < maxPredCol) {
            const pPreds = incomingByTarget.get(pid)
            let maxPpredCol = -1
            if (pPreds) {
              for (const ppid of pPreds) {
                const ppCol = nodeColMap.get(ppid) || 0
                if (ppCol > maxPpredCol) maxPpredCol = ppCol
              }
            }
            if (maxPredCol > maxPpredCol) {
              nodeColMap.set(pid, maxPredCol)
              alapChanged = true
            }
          }
        }
      }
    }

    // C. 前向拓撲約束保證 (所有邊方向皆為 col(src) < col(tgt))
    for (const c of flowConnections) {
      const srcCol = nodeColMap.get(c.from_node) || 0
      const tgtCol = nodeColMap.get(c.to_node) || 0
      if (srcCol >= tgtCol) {
        nodeColMap.set(c.to_node, srcCol + 1)
        alapChanged = true
      }
    }
  }

  const distinctCols = Array.from(new Set(mainNodes.map((n) => nodeColMap.get(n.id) || 0))).sort(
    (a, b) => a - b
  )
  const colRemap = new Map<number, number>()
  distinctCols.forEach((colVal, idx) => colRemap.set(colVal, idx))

  const stages: string[][] = Array.from({ length: distinctCols.length }, () => [])
  for (const n of mainNodes) {
    const compactCol = colRemap.get(nodeColMap.get(n.id) || 0) || 0
    nodeColMap.set(n.id, compactCol)
    stages[compactCol].push(n.id)
  }

  return { stages, nodeColMap }
}

/**
 * 為差分雙軌通道建立雙軌邏輯單元 (LogicalUnit) 並分配水平路徑帶 (Path Bands) 與各 Band 的 Y 座標
 */
export function assignDiffLogicalUnitsAndBands(params: {
  stages: string[][]
  nodeById: Map<string, UniversalNode>
  nodeOrderMap: Map<string, number>
  flowConnections: UniversalConnection[]
  allConnections: UniversalConnection[]
  compactTpNodes: UniversalNode[]
  getPinPolarity: (nodeId: string, pin: UniversalPin, idx: number) => 'p' | 'n'
  pBaseY: number
  nBaseY: number
}): {
  nodeBandMap: Map<string, number>
  bandRailYMap: Map<number, { pY: number; nY: number }>
} {
  const {
    stages,
    nodeById,
    nodeOrderMap,
    flowConnections,
    allConnections,
    compactTpNodes,
    getPinPolarity,
    pBaseY,
    nBaseY,
  } = params
  const numCols = stages.length
  const nodeBandMap = new Map<string, number>()
  const bandRailYMap = new Map<number, { pY: number; nY: number }>()
  const unitsByCol: LogicalUnit[][] = Array.from({ length: numCols }, () => [])
  const unitByNodeId = new Map<string, LogicalUnit>()

  const getDownstreamKey = (nid: string): string => {
    const targets = flowConnections.filter((c) => c.from_node === nid).map((c) => c.to_node)
    return Array.from(new Set(targets)).sort().join(',')
  }

  for (let c = 0; c < numCols; c++) {
    const stageIds = stages[c]
    const pPassives: UniversalNode[] = []
    const nPassives: UniversalNode[] = []

    for (const nid of stageIds) {
      const node = nodeById.get(nid)!
      if (isDualRailComponent(node)) {
        const isMounted = node.is_mounted !== false && node.isMounted !== false
        const unit: LogicalUnit = {
          id: `unit_${node.id}`,
          col: c,
          band: 0,
          dualNode: node,
          nodeIds: [node.id],
          isMounted,
          isBranchHint: node.lane === 'branch',
          isTapHint: node.lane === 'tap',
          isTerminal: node.role === 'terminal',
          orderIdx: nodeOrderMap.get(node.id) ?? 0,
        }
        unitsByCol[c].push(unit)
        unitByNodeId.set(node.id, unit)
      } else {
        const firstPin = node.pins[0]
        const isP = firstPin ? getPinPolarity(node.id, firstPin, 0) === 'p' : true
        if (isP) pPassives.push(node)
        else nPassives.push(node)
      }
    }

    const usedN = new Set<string>()
    const getPredUnitId = (nid: string): string => {
      for (const conn of flowConnections) {
        if (conn.to_node === nid) {
          const u = unitByNodeId.get(conn.from_node)
          if (u) return u.id
        }
      }
      return ''
    }

    for (const pNode of pPassives) {
      const pMounted = pNode.is_mounted !== false && pNode.isMounted !== false
      const pBranch = pNode.lane === 'branch'
      const pDownKey = getDownstreamKey(pNode.id)
      const pPredUnit = getPredUnitId(pNode.id)

      let partner = nPassives.find(
        (n) =>
          !usedN.has(n.id) &&
          (n.lane === 'branch') === pBranch &&
          (n.is_mounted !== false && n.isMounted !== false) === pMounted &&
          pDownKey !== '' &&
          getDownstreamKey(n.id) === pDownKey
      )
      if (!partner && pPredUnit !== '') {
        partner = nPassives.find(
          (n) => !usedN.has(n.id) && (n.lane === 'branch') === pBranch && getPredUnitId(n.id) === pPredUnit
        )
      }
      if (!partner) {
        partner = nPassives.find(
          (n) =>
            !usedN.has(n.id) &&
            (n.lane === 'branch') === pBranch &&
            (n.is_mounted !== false && n.isMounted !== false) === pMounted
        )
      }
      if (!partner) {
        partner = nPassives.find((n) => !usedN.has(n.id))
      }

      if (partner) {
        usedN.add(partner.id)
        const unit: LogicalUnit = {
          id: `unit_${pNode.id}_${partner.id}`,
          col: c,
          band: 0,
          pNode,
          nNode: partner,
          nodeIds: [pNode.id, partner.id],
          isMounted: pMounted,
          isBranchHint: pBranch,
          isTapHint: false,
          isTerminal: false,
          orderIdx: Math.min(nodeOrderMap.get(pNode.id) ?? 0, nodeOrderMap.get(partner.id) ?? 0),
        }
        unitsByCol[c].push(unit)
        unitByNodeId.set(pNode.id, unit)
        unitByNodeId.set(partner.id, unit)
      } else {
        const unit: LogicalUnit = {
          id: `unit_${pNode.id}`,
          col: c,
          band: 0,
          pNode,
          nodeIds: [pNode.id],
          isMounted: pMounted,
          isBranchHint: pBranch,
          isTapHint: false,
          isTerminal: false,
          orderIdx: nodeOrderMap.get(pNode.id) ?? 0,
        }
        unitsByCol[c].push(unit)
        unitByNodeId.set(pNode.id, unit)
      }
    }

    for (const nNode of nPassives) {
      if (usedN.has(nNode.id)) continue
      const nMounted = nNode.is_mounted !== false && nNode.isMounted !== false
      const unit: LogicalUnit = {
        id: `unit_${nNode.id}`,
        col: c,
        band: 0,
        nNode,
        nodeIds: [nNode.id],
        isMounted: nMounted,
        isBranchHint: nNode.lane === 'branch',
        isTapHint: false,
        isTerminal: false,
        orderIdx: nodeOrderMap.get(nNode.id) ?? 0,
      }
      unitsByCol[c].push(unit)
      unitByNodeId.set(nNode.id, unit)
    }
  }

  const unitSuccs = new Map<string, Set<LogicalUnit>>()
  const unitPreds = new Map<string, Set<LogicalUnit>>()
  for (const colUnits of unitsByCol) {
    for (const u of colUnits) {
      unitSuccs.set(u.id, new Set())
      unitPreds.set(u.id, new Set())
    }
  }
  for (const conn of flowConnections) {
    const uFrom = unitByNodeId.get(conn.from_node)
    const uTo = unitByNodeId.get(conn.to_node)
    if (uFrom && uTo && uFrom.id !== uTo.id && uFrom.col < uTo.col) {
      unitSuccs.get(uFrom.id)!.add(uTo)
      unitPreds.get(uTo.id)!.add(uFrom)
    }
  }

  const memoReachesConnector = new Map<string, boolean>()
  const reachesMountedConnector = (u: LogicalUnit): boolean => {
    if (memoReachesConnector.has(u.id)) return memoReachesConnector.get(u.id)!
    if (u.dualNode && u.isTerminal && u.isMounted && !u.isTapHint && isConnectorNode(u.dualNode)) {
      memoReachesConnector.set(u.id, true)
      return true
    }
    for (const nxt of unitSuccs.get(u.id) || []) {
      if (reachesMountedConnector(nxt)) {
        memoReachesConnector.set(u.id, true)
        return true
      }
    }
    memoReachesConnector.set(u.id, false)
    return false
  }

  const occupiedBandsAtCol: Set<number>[] = Array.from({ length: numCols }, () => new Set<number>())

  const reserveSpanningCorridor = (u: LogicalUnit) => {
    for (const nxt of unitSuccs.get(u.id) || []) {
      if (nxt.col > u.col + 1 && !nxt.isBranchHint && !u.isBranchHint) {
        for (let midCol = u.col + 1; midCol < nxt.col; midCol++) {
          occupiedBandsAtCol[midCol].add(u.band)
        }
      }
    }
  }

  for (let c = 0; c < numCols; c++) {
    const colUnits = unitsByCol[c]
    if (colUnits.length === 0) continue

    if (c === 0) {
      colUnits.sort((a, b) => a.orderIdx - b.orderIdx)
      colUnits.forEach((u, idx) => {
        u.band = idx
        occupiedBandsAtCol[c].add(idx)
        reserveSpanningCorridor(u)
        for (const nid of u.nodeIds) nodeBandMap.set(nid, u.band)
      })
      continue
    }

    const assignedUnits = new Set<string>()

    if (!occupiedBandsAtCol[c].has(0)) {
      const band0Candidates = colUnits.filter((u) => {
        if (u.isBranchHint || u.isTapHint) return false
        const preds = Array.from(unitPreds.get(u.id) || [])
        return preds.some((p) => p.band === 0)
      })

      if (band0Candidates.length > 0) {
        band0Candidates.sort((a, b) => {
          if (a.isMounted !== b.isMounted) return a.isMounted ? -1 : 1
          if (!a.isTerminal && !b.isTerminal) {
            const aConn = reachesMountedConnector(a)
            const bConn = reachesMountedConnector(b)
            if (aConn !== bConn) return aConn ? -1 : 1
          }
          const aHasSucc = (unitSuccs.get(a.id)?.size || 0) > 0
          const bHasSucc = (unitSuccs.get(b.id)?.size || 0) > 0
          if (aHasSucc !== bHasSucc) return aHasSucc ? -1 : 1
          return a.orderIdx - b.orderIdx
        })

        const winner = band0Candidates[0]
        winner.band = 0
        occupiedBandsAtCol[c].add(0)
        assignedUnits.add(winner.id)
        reserveSpanningCorridor(winner)
      }
    }

    for (const u of colUnits) {
      if (assignedUnits.has(u.id)) continue
      const preds = Array.from(unitPreds.get(u.id) || []).filter((p) => p.band > 0)
      if (preds.length > 0) {
        const targetBand = preds[0].band
        if (!occupiedBandsAtCol[c].has(targetBand)) {
          u.band = targetBand
          occupiedBandsAtCol[c].add(targetBand)
          assignedUnits.add(u.id)
          reserveSpanningCorridor(u)
        }
      }
    }

    const remaining = colUnits.filter((u) => !assignedUnits.has(u.id))
    remaining.sort((a, b) => {
      const aReconvergesToBand0 = Array.from(unitSuccs.get(a.id) || []).some(
        (s) => s.band === 0 || (!s.isBranchHint && !s.isTapHint && reachesMountedConnector(s))
      )
      const bReconvergesToBand0 = Array.from(unitSuccs.get(b.id) || []).some(
        (s) => s.band === 0 || (!s.isBranchHint && !s.isTapHint && reachesMountedConnector(s))
      )
      if ((a.isBranchHint && aReconvergesToBand0) !== (b.isBranchHint && bReconvergesToBand0)) {
        return a.isBranchHint && aReconvergesToBand0 ? -1 : 1
      }
      if (a.orderIdx !== b.orderIdx) return a.orderIdx - b.orderIdx
      return 0
    })

    for (const u of remaining) {
      let b = 1
      while (occupiedBandsAtCol[c].has(b)) {
        b++
      }
      u.band = b
      occupiedBandsAtCol[c].add(b)
      assignedUnits.add(u.id)
      reserveSpanningCorridor(u)
    }

    for (const u of colUnits) {
      for (const nid of u.nodeIds) {
        nodeBandMap.set(nid, u.band)
      }
    }
  }

  let maxBand = 0
  for (const colUnits of unitsByCol) {
    for (const u of colUnits) {
      if (u.band > maxBand) maxBand = u.band
    }
  }

  let prevBandMaxBottom = 0
  for (let b = 0; b <= maxBand; b++) {
    const unitsInBand: LogicalUnit[] = []
    for (const colUnits of unitsByCol) {
      for (const u of colUnits) {
        if (u.band === b) unitsInBand.push(u)
      }
    }

    const hasPairedPassivesInBand = unitsInBand.some((u) => !u.dualNode && (u.pNode || u.nNode))
    const railGap = b === 0 || hasPairedPassivesInBand ? 50 : 36

    let pY = pBaseY
    let nY = nBaseY
    if (b > 0) {
      let maxTopPadInBand = 28
      for (const u of unitsInBand) {
        const ext0 = getUnitVerticalExtent(u, 0, railGap, getPinPolarity)
        if (-ext0.top > maxTopPadInBand) maxTopPadInBand = -ext0.top
      }
      pY = Math.max(nBaseY + 50, prevBandMaxBottom + 18 + maxTopPadInBand)
      nY = pY + railGap
    }

    bandRailYMap.set(b, { pY, nY })

    let bandBottom = nY + 16
    if (b === 0 && compactTpNodes.length > 0) {
      const hasNTestPoint = compactTpNodes.some((tp) => {
        const conn = allConnections.find((c) => c.to_node === tp.id || c.from_node === tp.id)
        return conn && resolvePolarity(conn.rail_id, conn.net_name) === 'n'
      })
      if (hasNTestPoint) {
        bandBottom = Math.max(bandBottom, nY + 34)
      }
    }
    for (const u of unitsInBand) {
      const ext = getUnitVerticalExtent(u, pY, nY, getPinPolarity)
      if (ext.bottom > bandBottom) bandBottom = ext.bottom
    }
    prevBandMaxBottom = bandBottom
  }

  return { nodeBandMap, bandRailYMap }
}

