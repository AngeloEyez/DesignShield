/**
 * @file universalTopologyLayout.ts
 * @description 通用電路拓撲排版演算法核心 (Universal Circuit Topology Layout Engine)
 * 支援單端信號 (Single-ended)、差分對 (Differential Dual-Rail)、匯流排 (Bus)、
 * 上拉電阻 (Pull-up VCC)、接地分流 (Shunt Ground/TVS) 等所有電氣拓撲之自動佈局計算。
 * 具備同軌多引腳曼哈頓匯流/分流 (Multi-pin Merging/Splitting)、同階層多端點分支錯開佈局
 * 與實體電氣焊點 (Junction Dots ●) 精確計算。
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
    width = Math.max(76, refDesLen * 9 + 20, maxPinTextLen * 5.6 + 24)
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

  // 1.1 建立引腳極性精確對應表 (Pin Polarity Lookup based on connections)
  // 優先根據 data.connections 中實際連接的 rail_id 與 net_name 判定極性，避免純以 pin_name 正則誤判
  const nodePinPolarityMap = new Map<string, 'p' | 'n'>()
  for (const c of data.connections) {
    const isN = c.rail_id === 'n_rail' || /n|dn|-|_n$/i.test(c.net_name)
    const pol: 'p' | 'n' = isN ? 'n' : 'p'
    if (c.from_node && c.from_pin) {
      nodePinPolarityMap.set(`${c.from_node}#${c.from_pin}`, pol)
    }
    if (c.to_node && c.to_pin) {
      nodePinPolarityMap.set(`${c.to_node}#${c.to_pin}`, pol)
    }
  }

  const getPinPolarity = (nodeId: string, pin: UniversalPin, fallbackIdx: number): 'p' | 'n' => {
    const key = `${nodeId}#${pin.pin_number}`
    if (nodePinPolarityMap.has(key)) return nodePinPolarityMap.get(key)!
    if (/n|dn|-/i.test(pin.pin_name || '')) return 'n'
    if (/p|dp|\+/i.test(pin.pin_name || '')) return 'p'
    return fallbackIdx % 2 === 1 ? 'n' : 'p'
  }

  // 2. 拓撲排序 / 階層劃分 (Main Stem Stages)
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

    // 依尺寸預先評估
    for (const nid of stageIds) {
      const node = nodeById.get(nid)!
      const { width } = estimateNodeSize(node)
      if (width > maxStageWidth) maxStageWidth = width
    }

    let dualRailTerminalCountInStage = 0

    for (const nid of stageIds) {
      const node = nodeById.get(nid)!
      const { width } = estimateNodeSize(node)

      const isDualRailCMC = node.role === 'series' && (node.pins.length >= 4 || node.category.toLowerCase().includes('choke'))
      const isTerminal = node.role === 'terminal'

      let nodeX = curX

      if (isDiff) {
        if (isTerminal || isDualRailCMC) {
          // 雙軌元件 (Terminal IC/Connector 或跨軌 CMC)
          let nodePBaseY = pBaseY
          let nodeNBaseY = nBaseY

          if (isTerminal && dualRailTerminalCountInStage > 0) {
            // 同 stage 次要端點：向下垂直錯開，解決多端點重疊問題
            nodePBaseY = nBaseY + 65 + (dualRailTerminalCountInStage - 1) * 90
            nodeNBaseY = nodePBaseY + 50
          }
          if (isTerminal) {
            dualRailTerminalCountInStage++
          }

          const lNode: LayoutNode = {
            id: node.id,
            refDes: node.ref_des,
            category: node.category,
            role: node.role,
            partNumber: node.part_number,
            value: node.value,
            x: nodeX,
            y: 0,
            width,
            height: 0,
            ports: [],
          }

          if (isDualRailCMC) {
            // 共模扼流圈 CMC：兩軌皆具備輸入與輸出端口 (4 個 port)
            // 按照輸入與輸出朝向分別排列
            const inPins = node.pins.filter((p) => p.orientation === 'left')
            const outPins = node.pins.filter((p) => p.orientation === 'right')

            const pInPin = inPins.find((p, i) => getPinPolarity(node.id, p, i) === 'p') || node.pins[0]
            const pOutPin = outPins.find((p, i) => getPinPolarity(node.id, p, i) === 'p') || node.pins[1]
            const nInPin = inPins.find((p, i) => getPinPolarity(node.id, p, i) === 'n') || node.pins[2]
            const nOutPin = outPins.find((p, i) => getPinPolarity(node.id, p, i) === 'n') || node.pins[3]

            const actualHeight = Math.max(130, nBaseY - pBaseY + 40)
            const nodeY = Math.round((pBaseY + nBaseY) / 2 - actualHeight / 2)
            lNode.y = nodeY
            lNode.height = actualHeight

            if (pInPin) {
              lNode.ports.push({
                id: `${node.id}_${pInPin.pin_number}`,
                pinNumber: pInPin.pin_number,
                pinName: pInPin.pin_name,
                orientation: 'left',
                x: nodeX,
                y: pBaseY,
                relX: 0,
                relY: pBaseY - nodeY,
                polarity: 'p',
              })
            }
            if (pOutPin) {
              lNode.ports.push({
                id: `${node.id}_${pOutPin.pin_number}`,
                pinNumber: pOutPin.pin_number,
                pinName: pOutPin.pin_name,
                orientation: 'right',
                x: nodeX + width,
                y: pBaseY,
                relX: width,
                relY: pBaseY - nodeY,
                polarity: 'p',
              })
            }
            if (nInPin) {
              lNode.ports.push({
                id: `${node.id}_${nInPin.pin_number}`,
                pinNumber: nInPin.pin_number,
                pinName: nInPin.pin_name,
                orientation: 'left',
                x: nodeX,
                y: nBaseY,
                relX: 0,
                relY: nBaseY - nodeY,
                polarity: 'n',
              })
            }
            if (nOutPin) {
              lNode.ports.push({
                id: `${node.id}_${nOutPin.pin_number}`,
                pinNumber: nOutPin.pin_number,
                pinName: nOutPin.pin_name,
                orientation: 'right',
                x: nodeX + width,
                y: nBaseY,
                relX: width,
                relY: nBaseY - nodeY,
                polarity: 'n',
              })
            }
          } else {
            // 端點 IC / Connector (包含起點 TJ1、終點 TU2、P72 等)
            const pPins = node.pins.filter((p, i) => getPinPolarity(node.id, p, i) === 'p')
            const nPins = node.pins.filter((p, i) => getPinPolarity(node.id, p, i) === 'n')

            const isStart = sIdx === 0
            const orientation: 'left' | 'right' = isStart ? 'right' : 'left'

            // 計算各引腳的 Y 座標偏移 (同軌多引腳時垂直間隔 20px)
            const PIN_SPACING = 20
            const pinYList: { pin: UniversalPin; y: number; polarity: 'p' | 'n' }[] = []

            const getOffsets = (count: number) => {
              if (count <= 1) return [0]
              const startOffset = -((count - 1) * PIN_SPACING) / 2
              return Array.from({ length: count }, (_, i) => startOffset + i * PIN_SPACING)
            }

            const pOffsets = getOffsets(pPins.length)
            pPins.forEach((pin, idx) => {
              pinYList.push({ pin, y: nodePBaseY + pOffsets[idx], polarity: 'p' })
            })

            const nOffsets = getOffsets(nPins.length)
            nPins.forEach((pin, idx) => {
              pinYList.push({ pin, y: nodeNBaseY + nOffsets[idx], polarity: 'n' })
            })

            const allYs = pinYList.map((p) => p.y)
            const minY = allYs.length > 0 ? Math.min(...allYs) : nodePBaseY
            const maxY = allYs.length > 0 ? Math.max(...allYs) : nodeNBaseY

            const nodeY = Math.round(minY - 18)
            const nodeHeight = Math.max(52, Math.round(maxY + 18 - nodeY))
            lNode.y = nodeY
            lNode.height = nodeHeight

            for (const item of pinYList) {
              const relX = orientation === 'right' ? width : 0
              const relY = Math.round(item.y - nodeY)
              lNode.ports.push({
                id: `${node.id}_${item.pin.pin_number}`,
                pinNumber: item.pin.pin_number,
                pinName: item.pin.pin_name,
                orientation,
                x: nodeX + relX,
                y: item.y,
                relX,
                relY,
                polarity: item.polarity,
              })
            }
          }

          layoutNodes.push(lNode)
          nodePositionLookup.set(node.id, lNode)
        } else {
          // 單軌串聯元件 (例如 TC13 在 P 軌，TC14 在 N 軌)
          const firstPin = node.pins[0]
          const isP = firstPin ? getPinPolarity(node.id, firstPin, 0) === 'p' : true
          const targetY = isP ? pBaseY : nBaseY
          const { height } = estimateNodeSize(node)
          const nodeY = Math.round(targetY - height / 2)

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
                id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
                pinNumber: node.pins[0]?.pin_number || '1',
                pinName: node.pins[0]?.pin_name,
                orientation: 'left',
                x: nodeX,
                y: targetY,
                relX: 0,
                relY: height / 2,
                polarity: isP ? 'p' : 'n',
              },
              {
                id: `${node.id}_${node.pins[1]?.pin_number || '2'}`,
                pinNumber: node.pins[1]?.pin_number || '2',
                pinName: node.pins[1]?.pin_name,
                orientation: 'right',
                x: nodeX + width,
                y: targetY,
                relX: width,
                relY: height / 2,
                polarity: isP ? 'p' : 'n',
              },
            ],
          }
          layoutNodes.push(lNode)
          nodePositionLookup.set(node.id, lNode)
        }
      } else {
        // 單端信號或匯流排
        const { height } = estimateNodeSize(node)
        const nodeY = Math.round(singleBaseY - height / 2)
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
            id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
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
            id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
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
            id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
            pinNumber: node.pins[0]?.pin_number || '1',
            pinName: node.pins[0]?.pin_name,
            orientation: 'left',
            x: nodeX,
            y: singleBaseY,
            relX: 0,
            relY: height / 2,
          })
          lNode.ports.push({
            id: `${node.id}_${node.pins[1]?.pin_number || '2'}`,
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
    const conn = data.connections.find((c) => c.to_node === node.id || c.from_node === node.id)
    const hostNodeId = conn ? (conn.to_node === node.id ? conn.from_node : conn.to_node) : stages[0]?.[0]
    const hostLayout = hostNodeId ? nodePositionLookup.get(hostNodeId) : null

    const { width, height } = estimateNodeSize(node)
    const hostX = hostLayout ? hostLayout.x + hostLayout.width + 40 + pIdx * 70 : 120 + pIdx * 70
    const hostY = 28

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

    symbols.push({
      id: `gnd_${node.id}`,
      type: 'gnd',
      label: 'GND',
      x: hostX + width / 2,
      y: hostY + height + 10,
    })
  })

  // 5. 建立連線 (Edges)、分支/匯流焊點 (Junction Dots) 與 Net 標籤 (Net Labels)
  const edges: LayoutEdge[] = []
  const junctionDots: JunctionDot[] = []
  const netLabels: NetLabel[] = []
  const seenLabels = new Set<string>()

  // 5.1 來源端同軌多引腳匯流檢測 (Source Multi-pin Merging)
  // 當節點在同一軌道有多個引腳輸出至同一目標/網段時，在右側 14px 處先行折線匯流並打上實體焊點
  const sourceMergeMap = new Map<string, Point>()
  for (const node of layoutNodes) {
    if (node.role !== 'terminal') continue
    const rightPPorts = node.ports.filter((p) => p.orientation === 'right' && p.polarity === 'p')
    if (rightPPorts.length > 1) {
      const mergePoint: Point = { x: node.x + node.width + 14, y: pBaseY }
      sourceMergeMap.set(`${node.id}#p`, mergePoint)
      junctionDots.push({
        id: `merge_dot_${node.id}_p`,
        x: mergePoint.x,
        y: mergePoint.y,
        polarity: 'p',
      })
      rightPPorts.forEach((port, pIdx) => {
        edges.push({
          id: `internal_merge_${node.id}_p_${pIdx}`,
          netName: '',
          railId: 'p_rail',
          sourceId: node.id,
          targetId: node.id,
          start: { x: port.x, y: port.y },
          end: mergePoint,
          pathD: generateOrthogonalPath({ x: port.x, y: port.y }, mergePoint, 3, mergePoint.x),
          isBranch: false,
          polarity: 'p',
        })
      })
    }

    const rightNPorts = node.ports.filter((p) => p.orientation === 'right' && p.polarity === 'n')
    if (rightNPorts.length > 1) {
      const mergePoint: Point = { x: node.x + node.width + 14, y: nBaseY }
      sourceMergeMap.set(`${node.id}#n`, mergePoint)
      junctionDots.push({
        id: `merge_dot_${node.id}_n`,
        x: mergePoint.x,
        y: mergePoint.y,
        polarity: 'n',
      })
      rightNPorts.forEach((port, nIdx) => {
        edges.push({
          id: `internal_merge_${node.id}_n_${nIdx}`,
          netName: '',
          railId: 'n_rail',
          sourceId: node.id,
          targetId: node.id,
          start: { x: port.x, y: port.y },
          end: mergePoint,
          pathD: generateOrthogonalPath({ x: port.x, y: port.y }, mergePoint, 3, mergePoint.x),
          isBranch: false,
          polarity: 'n',
        })
      })
    }
  }

  // 5.2 目標端同軌多引腳分流檢測 (Target Multi-pin Splitting)
  // 當目標節點在同軌有多個引腳接收同一訊號時，在左側 14px 處設立分流點並打上實體焊點
  const targetSplitMap = new Map<string, Point>()
  for (const node of layoutNodes) {
    if (node.role !== 'terminal') continue
    const leftPPorts = node.ports.filter((p) => p.orientation === 'left' && p.polarity === 'p')
    if (leftPPorts.length > 1) {
      const splitPoint: Point = { x: node.x - 14, y: pBaseY }
      targetSplitMap.set(`${node.id}#p`, splitPoint)
      junctionDots.push({
        id: `split_dot_${node.id}_p`,
        x: splitPoint.x,
        y: splitPoint.y,
        polarity: 'p',
      })
      leftPPorts.forEach((port, pIdx) => {
        edges.push({
          id: `internal_split_${node.id}_p_${pIdx}`,
          netName: '',
          railId: 'p_rail',
          sourceId: node.id,
          targetId: node.id,
          start: splitPoint,
          end: { x: port.x, y: port.y },
          pathD: generateOrthogonalPath(splitPoint, { x: port.x, y: port.y }, 3, splitPoint.x),
          isBranch: false,
          polarity: 'p',
        })
      })
    }

    const leftNPorts = node.ports.filter((p) => p.orientation === 'left' && p.polarity === 'n')
    if (leftNPorts.length > 1) {
      const splitPoint: Point = { x: node.x - 14, y: nBaseY }
      targetSplitMap.set(`${node.id}#n`, splitPoint)
      junctionDots.push({
        id: `split_dot_${node.id}_n`,
        x: splitPoint.x,
        y: splitPoint.y,
        polarity: 'n',
      })
      leftNPorts.forEach((port, nIdx) => {
        edges.push({
          id: `internal_split_${node.id}_n_${nIdx}`,
          netName: '',
          railId: 'n_rail',
          sourceId: node.id,
          targetId: node.id,
          start: splitPoint,
          end: { x: port.x, y: port.y },
          pathD: generateOrthogonalPath(splitPoint, { x: port.x, y: port.y }, 3, splitPoint.x),
          isBranch: false,
          polarity: 'n',
        })
      })
    }
  }

  // 5.3 遍歷繪製 data.connections 連線
  const drawnStemConnections = new Set<string>()

  data.connections.forEach((conn, cIdx) => {
    const srcNode = nodePositionLookup.get(conn.from_node)
    const tgtNode = nodePositionLookup.get(conn.to_node)
    if (!srcNode || !tgtNode) return

    const isN = conn.rail_id === 'n_rail' || /n|dn|-|_n$/i.test(conn.net_name)
    const polarity: 'p' | 'n' = isN ? 'n' : 'p'
    const railKey = polarity

    // 尋找最適起點 Port (精確引腳匹配優先)
    let srcPort = srcNode.ports.find((p) => p.pinNumber === conn.from_pin)
    if (!srcPort) {
      srcPort = srcNode.ports.find((p) => (p.orientation === 'right' || p.orientation === 'bottom') && p.polarity === polarity)
    }
    if (!srcPort) {
      srcPort = srcNode.ports.find((p) => p.orientation === 'right' || p.orientation === 'bottom')
    }

    // 尋找最適終點 Port (精確引腳匹配優先)
    let tgtPort = tgtNode.ports.find((p) => p.pinNumber === conn.to_pin)
    if (!tgtPort) {
      tgtPort = tgtNode.ports.find((p) => (p.orientation === 'left' || p.orientation === 'top') && p.polarity === polarity)
    }
    if (!tgtPort) {
      tgtPort = tgtNode.ports.find((p) => p.orientation === 'left' || p.orientation === 'top')
    }

    // 判斷是否為同軌多引腳匯流/分流的主幹去重
    const hasSrcMerge = sourceMergeMap.has(`${conn.from_node}#${railKey}`)
    const hasTgtSplit = targetSplitMap.has(`${conn.to_node}#${railKey}`)

    const stemKey = `${conn.from_node}->${conn.to_node}#${railKey}#${conn.net_name}`
    if ((hasSrcMerge || hasTgtSplit) && drawnStemConnections.has(stemKey)) {
      // 匯流/分流內已繪製過此主幹訊號線，避免重複疊加
      return
    }
    drawnStemConnections.add(stemKey)

    const start: Point = hasSrcMerge
      ? sourceMergeMap.get(`${conn.from_node}#${railKey}`)!
      : srcPort
        ? { x: srcPort.x, y: srcPort.y }
        : { x: srcNode.x + srcNode.width, y: srcNode.y + srcNode.height / 2 }

    const end: Point = hasTgtSplit
      ? targetSplitMap.get(`${conn.to_node}#${railKey}`)!
      : tgtPort
        ? { x: tgtPort.x, y: tgtPort.y }
        : { x: tgtNode.x, y: tgtNode.y + tgtNode.height / 2 }

    const labelWidth = Math.ceil(conn.net_name.length * 5.0)
    let pathD = ''

    // 判斷是否為向下垂直錯開的次要端點分支連線 (如 P72 接在下方)
    const isDownwardTerminalBranch = tgtPort && tgtPort.y > nBaseY + 20 && !conn.is_branch

    if (conn.is_branch) {
      // 垂直支路連接 (上拉/接地)
      const junctionX = tgtPort ? tgtPort.x : (start.x + end.x) / 2
      const junctionY = start.y
      pathD = `M ${junctionX} ${junctionY} L ${end.x} ${end.y}`

      junctionDots.push({
        id: `junc_branch_${cIdx}`,
        x: junctionX,
        y: junctionY,
        polarity,
      })
    } else if (isDownwardTerminalBranch && tgtPort) {
      // 下方次要端點分支連線：自上方主幹分支出直角曼哈頓折線，在交會處打焊點
      const trunkY = isN ? nBaseY : pBaseY
      const tapX = Math.max(start.x + labelWidth + 16, tgtPort.x - 22)
      pathD = generateOrthogonalPath({ x: tapX, y: trunkY }, end, 4, tapX)

      junctionDots.push({
        id: `junc_tap_${cIdx}_${tgtNode.id}`,
        x: tapX,
        y: trunkY,
        polarity,
      })
    } else {
      // 標準主幹訊號線
      const bendX = Math.max((start.x + end.x) / 2, start.x + labelWidth + 14)
      pathD = generateOrthogonalPath(start, end, 4, bendX)

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
      isBranch: Boolean(conn.is_branch || isDownwardTerminalBranch),
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
  for (const e of edges) {
    if (e.end.x > maxX) maxX = e.end.x
    if (e.end.y > maxY) maxY = e.end.y
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
