/**
 * @file universalTopologyLayout.ts
 * @description 通用電路拓撲排版演算法核心 (Universal Circuit Topology Layout Engine)
 * 支援單端信號 (Single-ended)、差分對 (Differential Dual-Rail)、匯流排 (Bus)、
 * 上拉電阻 (Pull-up VCC)、接地分流 (Shunt Ground/TVS) 等所有電氣拓撲之自動佈局計算。
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
  role: 'terminal' | 'series' | 'pull_up' | 'pull_down' | 'shunt_ground' | 'bridge' | string
  part_number?: string
  value?: string
  pins: UniversalPin[]
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
 * 曼哈頓直角階梯折線產生器 (含半徑 4px 微圓角)
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
 * 估算節點寬度與高度
 */
function estimateNodeSize(node: UniversalNode): { width: number; height: number } {
  const isTerminal = node.role === 'terminal'
  const isPassive = node.role === 'series' || node.role === 'pull_up' || node.role === 'shunt_ground' || node.role === 'pull_down'

  const refDesLen = node.ref_des.length
  let maxPinTextLen = 0
  for (const p of node.pins) {
    const textLen = (p.pin_number?.length || 0) + (p.pin_name ? p.pin_name.length + 2 : 0)
    if (textLen > maxPinTextLen) maxPinTextLen = textLen
  }

  let width = 60
  if (isTerminal) {
    width = Math.max(72, refDesLen * 8 + 24, maxPinTextLen * 6.5 + 24)
  } else if (isPassive) {
    const valLen = node.value ? node.value.length * 6 : 0
    width = Math.max(56, refDesLen * 7 + 16, valLen + 16)
  }

  let height = 38
  if (isTerminal) {
    if (node.pins.length > 1) {
      height = Math.max(52, 28 + (node.pins.length - 1) * 22)
    }
  } else if (node.role === 'pull_up' || node.role === 'shunt_ground') {
    height = 36
  }

  return { width: Math.round(width), height: Math.round(height) }
}

/**
 * 通用電路拓撲排版計算主入口
 */
export function computeUniversalTopologyLayout(
  inputData: UniversalTopologyData | Record<string, any> | undefined
): UniversalTopologyLayout {
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

  const channelType = data.channel_type || 'single'
  const title = data.title || ''
  const isDiff = channelType === 'differential'

  // 1. 分類節點：主幹元件 vs 垂直支路元件
  const mainNodes: UniversalNode[] = []
  const pullUpNodes: UniversalNode[] = []
  const shuntNodes: UniversalNode[] = []

  const nodeById = new Map<string, UniversalNode>()
  for (const n of data.nodes) {
    nodeById.set(n.id, n)
    if (n.role === 'pull_up') {
      pullUpNodes.push(n)
    } else if (n.role === 'shunt_ground' || n.role === 'pull_down') {
      shuntNodes.push(n)
    } else {
      mainNodes.push(n)
    }
  }

  // 2. 拓撲排序 / 階層劃分 (Main Stem Stages)
  // 建立連線圖以決定從左至右的 stage
  const inDegree = new Map<string, number>()
  const adjList = new Map<string, string[]>()
  for (const n of mainNodes) {
    inDegree.set(n.id, 0)
    adjList.set(n.id, [])
  }

  for (const c of data.connections) {
    if (c.is_branch) continue
    if (adjList.has(c.from_node) && adjList.has(c.to_node)) {
      adjList.get(c.from_node)!.push(c.to_node)
      inDegree.set(c.to_node, (inDegree.get(c.to_node) || 0) + 1)
    }
  }

  // 若無明確連線入度，以預設先後排序
  const stages: string[][] = []
  const visited = new Set<string>()
  const startNodes = mainNodes.filter((n) => (inDegree.get(n.id) || 0) === 0).map((n) => n.id)

  let queue = startNodes.length > 0 ? [...startNodes] : [mainNodes[0].id]
  while (queue.length > 0) {
    const nextQueue: string[] = []
    const currentStage: string[] = []
    for (const u of queue) {
      if (visited.has(u)) continue
      visited.add(u)
      currentStage.push(u)
      const neighbors = adjList.get(u) || []
      for (const v of neighbors) {
        if (!visited.has(v)) {
          nextQueue.push(v)
        }
      }
    }
    if (currentStage.length > 0) {
      stages.push(currentStage)
    }
    queue = Array.from(new Set(nextQueue))
  }

  // 補齊未被訪到的主幹節點
  const unvisited = mainNodes.filter((n) => !visited.has(n.id))
  if (unvisited.length > 0) {
    stages.push(unvisited.map((n) => n.id))
  }

  // 3. 幾何定位運算 (X/Y Coordinate Computation)
  const layoutNodes: LayoutNode[] = []
  const nodePositionLookup = new Map<string, LayoutNode>()

  let curX = 36
  const pBaseY = 85
  const nBaseY = 175
  const singleBaseY = 90

  for (let sIdx = 0; sIdx < stages.length; sIdx++) {
    const stageIds = stages[sIdx]
    let maxStageWidth = 0

    // 先計算 stage 內各節點尺寸
    for (const nid of stageIds) {
      const node = nodeById.get(nid)!
      const { width } = estimateNodeSize(node)
      if (width > maxStageWidth) maxStageWidth = width
    }

    for (const nid of stageIds) {
      const node = nodeById.get(nid)!
      const { width, height } = estimateNodeSize(node)

      let nodeX = curX
      let nodeY = 0

      // 檢查是否為差分通道
      if (isDiff) {
        const hasN = node.pins.some((p) => /n|dn|-|tx1|rx1/i.test(p.pin_name || p.pin_number))
        const isDualRailCMC = node.role === 'series' && (node.pins.length >= 4 || node.category.toLowerCase().includes('choke'))
        const isTerminal = node.role === 'terminal'

        if (isTerminal || isDualRailCMC) {
          // 雙軌元件 (IC、Connector 或跨軌共模扼流圈 CMC)
          const actualHeight = Math.max(height, 130)
          nodeY = Math.round((pBaseY + nBaseY) / 2 - actualHeight / 2)
          const lNode: LayoutNode = {
            id: node.id,
            refDes: node.ref_des,
            category: node.category,
            role: node.role,
            partNumber: node.part_number,
            value: node.value,
            x: nodeX,
            y: nodeY,
            width,
            height: actualHeight,
            ports: [],
          }

          const pRelY = pBaseY - nodeY
          const nRelY = nBaseY - nodeY

          if (isDualRailCMC) {
            // 共模扼流圈 CMC：兩軌皆具備輸入與輸出端口 (4 個 port)
            const pInPin = node.pins[0]?.pin_number || '3'
            const pOutPin = node.pins[1]?.pin_number || '4'
            const nInPin = node.pins[2]?.pin_number || '2'
            const nOutPin = node.pins[3]?.pin_number || '1'

            lNode.ports.push({
              id: `${node.id}_p_in`,
              pinNumber: pInPin,
              pinName: node.pins[0]?.pin_name,
              orientation: 'left',
              x: nodeX,
              y: pBaseY,
              relX: 0,
              relY: pRelY,
            })
            lNode.ports.push({
              id: `${node.id}_p_out`,
              pinNumber: pOutPin,
              pinName: node.pins[1]?.pin_name,
              orientation: 'right',
              x: nodeX + width,
              y: pBaseY,
              relX: width,
              relY: pRelY,
            })
            lNode.ports.push({
              id: `${node.id}_n_in`,
              pinNumber: nInPin,
              pinName: node.pins[2]?.pin_name,
              orientation: 'left',
              x: nodeX,
              y: nBaseY,
              relX: 0,
              relY: nRelY,
            })
            lNode.ports.push({
              id: `${node.id}_n_out`,
              pinNumber: nOutPin,
              pinName: node.pins[3]?.pin_name,
              orientation: 'right',
              x: nodeX + width,
              y: nBaseY,
              relX: width,
              relY: nRelY,
            })
          } else {
            // 端點 IC / Connector
            const pPorts = node.pins.filter((p) => !/n|dn|-/i.test(p.pin_name || ''))
            const nPorts = node.pins.filter((p) => /n|dn|-/i.test(p.pin_name || ''))
            const portDir = sIdx === 0 ? 'out' : sIdx === stages.length - 1 ? 'in' : 'both'

            if (portDir === 'out' || portDir === 'both') {
              lNode.ports.push({
                id: `${node.id}_p_out`,
                pinNumber: pPorts[0]?.pin_number || '1',
                pinName: pPorts[0]?.pin_name,
                orientation: 'right',
                x: nodeX + width,
                y: pBaseY,
                relX: width,
                relY: pRelY,
              })
              lNode.ports.push({
                id: `${node.id}_n_out`,
                pinNumber: nPorts[0]?.pin_number || '2',
                pinName: nPorts[0]?.pin_name,
                orientation: 'right',
                x: nodeX + width,
                y: nBaseY,
                relX: width,
                relY: nRelY,
              })
            }
            if (portDir === 'in' || portDir === 'both') {
              lNode.ports.push({
                id: `${node.id}_p_in`,
                pinNumber: pPorts[0]?.pin_number || '1',
                pinName: pPorts[0]?.pin_name,
                orientation: 'left',
                x: nodeX,
                y: pBaseY,
                relX: 0,
                relY: pRelY,
              })
              lNode.ports.push({
                id: `${node.id}_n_in`,
                pinNumber: nPorts[0]?.pin_number || '2',
                pinName: nPorts[0]?.pin_name,
                orientation: 'left',
                x: nodeX,
                y: nBaseY,
                relX: 0,
                relY: nRelY,
              })
            }
          }

          layoutNodes.push(lNode)
          nodePositionLookup.set(node.id, lNode)
        } else {
          // 單軌串聯元件 (如 TC13 在 P 軌，TC14 在 N 軌)
          const isP = !hasN
          const targetY = isP ? pBaseY : nBaseY
          nodeY = targetY - height / 2

          const lNode: LayoutNode = {
            id: node.id,
            refDes: node.ref_des,
            category: node.category,
            role: node.role,
            partNumber: node.part_number,
            value: node.value,
            x: nodeX,
            y: nodeY,
            width,
            height,
            ports: [
              {
                id: `${node.id}_in`,
                pinNumber: node.pins[0]?.pin_number || '1',
                pinName: node.pins[0]?.pin_name,
                orientation: 'left',
                x: nodeX,
                y: targetY,
                relX: 0,
                relY: height / 2,
              },
              {
                id: `${node.id}_out`,
                pinNumber: node.pins[1]?.pin_number || '2',
                pinName: node.pins[1]?.pin_name,
                orientation: 'right',
                x: nodeX + width,
                y: targetY,
                relX: width,
                relY: height / 2,
              },
            ],
          }
          layoutNodes.push(lNode)
          nodePositionLookup.set(node.id, lNode)
        }
      } else {
        // 單端信號或匯流排
        nodeY = singleBaseY - height / 2
        const lNode: LayoutNode = {
          id: node.id,
          refDes: node.ref_des,
          category: node.category,
          role: node.role,
          partNumber: node.part_number,
          value: node.value,
          x: nodeX,
          y: nodeY,
          width,
          height,
          ports: [],
        }

        const isStart = sIdx === 0
        const isEnd = sIdx === stages.length - 1
        if (isStart) {
          lNode.ports.push({
            id: `${node.id}_out`,
            pinNumber: node.pins[0]?.pin_number || '1',
            pinName: node.pins[0]?.pin_name,
            orientation: 'right',
            x: nodeX + width,
            y: singleBaseY,
            relX: width,
            relY: height / 2,
          })
        } else if (isEnd) {
          lNode.ports.push({
            id: `${node.id}_in`,
            pinNumber: node.pins[0]?.pin_number || '1',
            pinName: node.pins[0]?.pin_name,
            orientation: 'left',
            x: nodeX,
            y: singleBaseY,
            relX: 0,
            relY: height / 2,
          })
        } else {
          lNode.ports.push({
            id: `${node.id}_in`,
            pinNumber: node.pins[0]?.pin_number || '1',
            pinName: node.pins[0]?.pin_name,
            orientation: 'left',
            x: nodeX,
            y: singleBaseY,
            relX: 0,
            relY: height / 2,
          })
          lNode.ports.push({
            id: `${node.id}_out`,
            pinNumber: node.pins[1]?.pin_number || '2',
            pinName: node.pins[1]?.pin_name,
            orientation: 'right',
            x: nodeX + width,
            y: singleBaseY,
            relX: width,
            relY: height / 2,
          })
        }

        layoutNodes.push(lNode)
        nodePositionLookup.set(node.id, lNode)
      }
    }

    // 計算下一個 stage X 間距 (考量 net label 佔位長度)
    const stageConns = data.connections.filter((c) => stageIds.includes(c.from_node))
    let maxNetLabelLen = 0
    for (const sc of stageConns) {
      if (sc.net_name.length > maxNetLabelLen) maxNetLabelLen = sc.net_name.length
    }
    const netGap = Math.max(90, maxNetLabelLen * 5.2 + 36)
    curX += maxStageWidth + netGap
  }

  // 4. 定位垂直支路節點 (上拉 Pull-Up 至 VCC / 接地分流 Shunt 至 GND)
  const symbols: ElectricalSymbol[] = []

  // 4.1 上拉節點 (Pull-Up)
  pullUpNodes.forEach((node, pIdx) => {
    // 依 connection 找到連接的主幹節點
    const conn = data.connections.find((c) => c.to_node === node.id || c.from_node === node.id)
    const hostNodeId = conn ? (conn.to_node === node.id ? conn.from_node : conn.to_node) : stages[0]?.[0]
    const hostLayout = hostNodeId ? nodePositionLookup.get(hostNodeId) : null

    const { width, height } = estimateNodeSize(node)
    const hostX = hostLayout ? hostLayout.x + hostLayout.width + 40 + pIdx * 70 : 120 + pIdx * 70
    const hostY = 28 // 頂部

    const lNode: LayoutNode = {
      id: node.id,
      refDes: node.ref_des,
      category: node.category,
      role: 'pull_up',
      partNumber: node.part_number,
      value: node.value,
      x: hostX,
      y: hostY,
      width,
      height,
      ports: [
        {
          id: `${node.id}_top`,
          pinNumber: '2',
          pinName: 'VCC',
          orientation: 'top',
          x: hostX + width / 2,
          y: hostY,
          relX: width / 2,
          relY: 0,
        },
        {
          id: `${node.id}_bot`,
          pinNumber: '1',
          pinName: 'SIG',
          orientation: 'bottom',
          x: hostX + width / 2,
          y: hostY + height,
          relX: width / 2,
          relY: height,
        },
      ],
    }
    layoutNodes.push(lNode)
    nodePositionLookup.set(node.id, lNode)

    // 加入頂部電源符號
    symbols.push({
      id: `vcc_${node.id}`,
      type: 'vcc',
      label: node.pins.find((p) => p.orientation === 'top')?.pin_name || '+3.3V',
      x: hostX + width / 2,
      y: hostY - 10,
    })
  })

  // 4.2 接地分流節點 (Shunt Ground)
  shuntNodes.forEach((node, sIdx) => {
    const conn = data.connections.find((c) => c.to_node === node.id || c.from_node === node.id)
    const hostNodeId = conn ? (conn.to_node === node.id ? conn.from_node : conn.to_node) : stages[0]?.[0]
    const hostLayout = hostNodeId ? nodePositionLookup.get(hostNodeId) : null

    const { width, height } = estimateNodeSize(node)
    const hostX = hostLayout ? hostLayout.x + hostLayout.width + 50 + sIdx * 70 : 160 + sIdx * 70
    const hostY = isDiff ? nBaseY + 45 : singleBaseY + 45

    const lNode: LayoutNode = {
      id: node.id,
      refDes: node.ref_des,
      category: node.category,
      role: 'shunt_ground',
      partNumber: node.part_number,
      value: node.value,
      x: hostX,
      y: hostY,
      width,
      height,
      ports: [
        {
          id: `${node.id}_top`,
          pinNumber: '1',
          pinName: 'SIG',
          orientation: 'top',
          x: hostX + width / 2,
          y: hostY,
          relX: width / 2,
          relY: 0,
        },
        {
          id: `${node.id}_bot`,
          pinNumber: '2',
          pinName: 'GND',
          orientation: 'bottom',
          x: hostX + width / 2,
          y: hostY + height,
          relX: width / 2,
          relY: height,
        },
      ],
    }
    layoutNodes.push(lNode)
    nodePositionLookup.set(node.id, lNode)

    // 加入底部接地符號
    symbols.push({
      id: `gnd_${node.id}`,
      type: 'gnd',
      label: 'GND',
      x: hostX + width / 2,
      y: hostY + height + 10,
    })
  })

  // 5. 建立連線 (Edges)、分支焊點 (Junction Dots) 與 Net 標籤 (Net Labels)
  const edges: LayoutEdge[] = []
  const junctionDots: JunctionDot[] = []
  const netLabels: NetLabel[] = []
  const seenLabels = new Set<string>()

  data.connections.forEach((conn, cIdx) => {
    const srcNode = nodePositionLookup.get(conn.from_node)
    const tgtNode = nodePositionLookup.get(conn.to_node)
    if (!srcNode || !tgtNode) return

    // 尋找最適起訖 Port
    let srcPort = srcNode.ports.find((p) => p.orientation === 'right' || p.orientation === 'bottom')
    if (conn.is_branch && (srcNode.role === 'pull_up' || srcNode.role === 'shunt_ground')) {
      srcPort = srcNode.ports.find((p) => p.orientation === (srcNode.role === 'pull_up' ? 'bottom' : 'top'))
    }

    let tgtPort = tgtNode.ports.find((p) => p.orientation === 'left' || p.orientation === 'top')
    if (conn.is_branch && (tgtNode.role === 'pull_up' || tgtNode.role === 'shunt_ground')) {
      tgtPort = tgtNode.ports.find((p) => p.orientation === (tgtNode.role === 'pull_up' ? 'bottom' : 'top'))
    }

    // 差分對極性匹配
    const isN = /n|dn|-/i.test(conn.net_name) || conn.rail_id === 'n_rail'
    const polarity: 'p' | 'n' = isN ? 'n' : 'p'

    if (isDiff && srcNode.ports.length > 2) {
      const matchPort = srcNode.ports.find((p) => p.orientation === 'right' && (isN ? p.y > 130 : p.y < 130))
      if (matchPort) srcPort = matchPort
    }
    if (isDiff && tgtNode.ports.length > 2) {
      const matchPort = tgtNode.ports.find((p) => p.orientation === 'left' && (isN ? p.y > 130 : p.y < 130))
      if (matchPort) tgtPort = matchPort
    }

    const start: Point = srcPort ? { x: srcPort.x, y: srcPort.y } : { x: srcNode.x + srcNode.width, y: srcNode.y + srcNode.height / 2 }
    const end: Point = tgtPort ? { x: tgtPort.x, y: tgtPort.y } : { x: tgtNode.x, y: tgtNode.y + tgtNode.height / 2 }

    const labelWidth = Math.ceil(conn.net_name.length * 5.0)
    let pathD = ''

    if (conn.is_branch) {
      // 垂直支路連接 (例如從主幹引到上拉/接地)
      // 直角曼哈頓折線：在 tgtPort.x 處與主幹相交
      const junctionX = tgtPort ? tgtPort.x : (start.x + end.x) / 2
      const junctionY = start.y
      pathD = `M ${junctionX} ${junctionY} L ${end.x} ${end.y}`

      // 在主幹相交處打上實體電氣焊點
      junctionDots.push({
        id: `junc_branch_${cIdx}`,
        x: junctionX,
        y: junctionY,
        polarity,
      })
    } else {
      // 主幹訊號線
      const bendX = Math.max((start.x + end.x) / 2, start.x + labelWidth + 14)
      pathD = generateOrthogonalPath(start, end, 4, bendX)

      // 標註 Net 名稱標籤
      if (conn.net_name && !seenLabels.has(conn.net_name)) {
        seenLabels.add(conn.net_name)
        netLabels.push({
          id: `lbl_${cIdx}_${conn.net_name}`,
          net: conn.net_name,
          x: start.x + 6,
          y: start.y - 3.5,
          width: labelWidth,
          height: 10,
          polarity,
        })
      }
    }

    edges.push({
      id: `edge_${cIdx}`,
      netName: conn.net_name,
      railId: conn.rail_id,
      sourceId: conn.from_node,
      targetId: conn.to_node,
      start,
      end,
      pathD,
      isBranch: Boolean(conn.is_branch),
      polarity,
    })
  })

  // 6. 計算整體 SVG 畫布邊界
  let maxX = 300
  let maxY = isDiff ? 230 : 160
  for (const n of layoutNodes) {
    if (n.x + n.width > maxX) maxX = n.x + n.width
    if (n.y + n.height > maxY) maxY = n.y + n.height
  }
  for (const s of symbols) {
    if (s.x > maxX) maxX = s.x
    if (s.y > maxY) maxY = s.y
  }

  const finalWidth = maxX + 40
  const finalHeight = Math.max(maxY + 35, isDiff ? 240 : 140)

  return {
    width: finalWidth,
    height: finalHeight,
    title,
    channelType,
    nodes: layoutNodes,
    edges,
    junctionDots,
    netLabels,
    symbols,
  }
}
