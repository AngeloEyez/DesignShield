/**
 * @file universalTopologyLayout.ts
 * @description 通用電路拓撲排版演算法核心 (Universal Circuit Topology Layout Engine)
 * 採用「分層有向無環圖 + 水平路徑帶 (Layered DAG + Path Bands)」通用架構：
 * 1. 支援單端信號 (Single-ended)、差分對 (Differential Dual-Rail)、匯流排 (Bus)、
 *    上拉電阻 (Pull-up VCC)、接地分流 (Shunt Ground/TVS)、中繼穿透晶片 (Inline Relay IC)
 *    與單腳測試點 (Compact Single-Pin Test Point TP*)。
 * 2. 基於網路與節點拓撲位勢進行自動階層對齊 (Stage Columns)，並將多分支/並聯/備用路徑
 *    自動分配至獨立水平路徑帶 (Band 0..K)，確保同路徑帶內元件水平直連、跨路徑帶轉折分槽走線。
 * 3. 幾何驅動之 Net Name 標籤定位：所有網路名稱直接錨定於該網路實際繪製之無遮擋水平線段正上方，
 *    徹底杜絕線條重疊、文字錯位與懸空標籤。
 */

import {
  type UniversalPin,
  type UniversalNode,
  type UniversalConnection,
  type UniversalRail,
  type UniversalTopologyData,
  type Point,
  type LayoutPort,
  type LayoutNode,
  type LayoutEdge,
  type JunctionDot,
  type NetLabel,
  type ElectricalSymbol,
  type UniversalTopologyLayout,
  type HorizontalSegmentRecord,
  generateOrthogonalPath,
  isTestPointNode,
  isDualRailComponent,
  estimateNodeSize,
  resolvePolarity,
  computeStageColumns,
  assignDiffLogicalUnitsAndBands,
} from './universalTopologyHelpers'

export {
  type UniversalPin,
  type UniversalNode,
  type UniversalConnection,
  type UniversalRail,
  type UniversalTopologyData,
  type Point,
  type LayoutPort,
  type LayoutNode,
  type LayoutEdge,
  type JunctionDot,
  type NetLabel,
  type ElectricalSymbol,
  type UniversalTopologyLayout,
  generateOrthogonalPath,
  resolvePolarity,
}

/**
 * 通用電路拓撲排版計算主入口
 *
 * @param {UniversalTopologyData | Record<string, any> | undefined} inputData - 原始拓撲資料
 * @returns {UniversalTopologyLayout} 完整 SVG 幾何排版結果
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

  // 1. 建立引腳極性精確對應表 (Pin Polarity Lookup based on connections)
  const nodePinPolarityMap = new Map<string, 'p' | 'n'>()
  for (const c of data.connections) {
    const pol = resolvePolarity(c.rail_id, c.net_name)
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
    const name = pin.pin_name || ''
    if (
      /(?:_N|_DN|_DM|D-)(?:\b|\d+|_|$)/i.test(name) ||
      /(?:^|_)N$/i.test(name) ||
      /-(?:\b|\d+|_|$)/.test(name)
    ) {
      return 'n'
    }
    if (
      /(?:_P|_DP|D\+)(?:\b|\d+|_|$)/i.test(name) ||
      /(?:^|_)P$/i.test(name) ||
      /\+(?:\b|\d+|_|$)/.test(name)
    ) {
      return 'p'
    }
    return fallbackIdx % 2 === 1 ? 'n' : 'p'
  }

  // 2. 分類節點：主幹/支路流向節點 (mainNodes)、中途單腳測試點 (compactTpNodes)、垂直支路 (pullUp/shunt)
  const rawMainNodes: UniversalNode[] = []
  const pullUpNodes: UniversalNode[] = []
  const shuntNodes: UniversalNode[] = []
  const nodeById = new Map<string, UniversalNode>()
  const nodeOrderMap = new Map<string, number>()

  data.nodes.forEach((n, idx) => {
    nodeById.set(n.id, n)
    nodeOrderMap.set(n.id, idx)
    if (n.role === 'pull_up') {
      pullUpNodes.push(n)
    } else if (n.role === 'shunt_ground' || n.role === 'pull_down') {
      shuntNodes.push(n)
    } else {
      rawMainNodes.push(n)
    }
  })

  // 判斷是否存在非測試點之真實端點 (若存在，則將單引腳測試點 TP* 抽離為緊湊掛載節點，不佔用主車道或 Stage)
  const hasNonTpTerminal = rawMainNodes.some((n) => n.role === 'terminal' && !isTestPointNode(n))
  const outgoingFlowCount = new Map<string, number>()
  for (const c of data.connections) {
    outgoingFlowCount.set(c.from_node, (outgoingFlowCount.get(c.from_node) || 0) + 1)
  }

  const mainNodes: UniversalNode[] = []
  const compactTpNodes: UniversalNode[] = []
  for (const n of rawMainNodes) {
    const isSinglePinTp =
      isDiff &&
      hasNonTpTerminal &&
      n.pins.length === 1 &&
      isTestPointNode(n) &&
      (outgoingFlowCount.get(n.id) || 0) === 0
    if (isSinglePinTp) {
      compactTpNodes.push(n)
    } else {
      mainNodes.push(n)
    }
  }
  const mainNodeIdSet = new Set(mainNodes.map((n) => n.id))

  // 3. 基於網路與節點之 DAG 最長路徑分層演算法 (Stage Column Layering)
  const flowConnections = data.connections.filter(
    (c) => mainNodeIdSet.has(c.from_node) && mainNodeIdSet.has(c.to_node) && c.from_node !== c.to_node
  )
  const { stages, nodeColMap } = computeStageColumns(mainNodes, flowConnections)

  const numCols = stages.length
  const layoutNodes: LayoutNode[] = []
  const nodePositionLookup = new Map<string, LayoutNode>()
  let nodeBandMap = new Map<string, number>()
  let bandRailYMap = new Map<number, { pY: number; nY: number }>()

  const pBaseY = 65
  const nBaseY = 115
  const singleBaseY = 80

  if (isDiff) {
    // 4A. 差分雙軌通道：建立雙軌邏輯單元 (LogicalUnit) 並分配水平路徑帶 (Path Bands)
    const bandResult = assignDiffLogicalUnitsAndBands({
      stages,
      nodeById,
      nodeOrderMap,
      flowConnections,
      allConnections: data.connections,
      compactTpNodes,
      getPinPolarity,
      pBaseY,
      nBaseY,
    })
    nodeBandMap = bandResult.nodeBandMap
    bandRailYMap = bandResult.bandRailYMap

    // 計算每個 Stage Column 的寬度與欄位間距 (colGap)
    const colWidths: number[] = []
    for (let c = 0; c < numCols; c++) {
      let maxW = 60
      for (const nid of stages[c]) {
        const { width } = estimateNodeSize(nodeById.get(nid)!)
        if (width > maxW) maxW = width
      }
      colWidths.push(maxW)
    }

    const colX: number[] = new Array(numCols).fill(36)
    for (let c = 0; c < numCols - 1; c++) {
      const connsInGap = flowConnections.filter((conn) => {
        const sc = nodeColMap.get(conn.from_node) ?? 0
        const tc = nodeColMap.get(conn.to_node) ?? 0
        return sc === c || (sc < c && tc === c + 1)
      })

      let maxNetWireLen = 36
      for (const sc of connsInGap) {
        const netStr = sc.net_name || ''
        const textWidth = Math.ceil(netStr.length * 5.3)
        const requiredWireLen = textWidth + 28
        if (requiredWireLen > maxNetWireLen) {
          maxNetWireLen = requiredWireLen
        }
      }

      const hasUpwardFromCol = flowConnections.some((conn) => {
        const sc = nodeColMap.get(conn.from_node) ?? 0
        const sb = nodeBandMap.get(conn.from_node) ?? 0
        const tb = nodeBandMap.get(conn.to_node) ?? 0
        return sc === c && sb > tb
      })

      const downwardNetsIntoNextCol = new Set<string>()
      for (const conn of flowConnections) {
        const tc = nodeColMap.get(conn.to_node) ?? 0
        const sb = nodeBandMap.get(conn.from_node) ?? 0
        const tb = nodeBandMap.get(conn.to_node) ?? 0
        if (tc === c + 1 && tb > sb) {
          downwardNetsIntoNextCol.add(`${conn.rail_id}#${conn.net_name}`)
        }
      }

      const hasCompactTpInGap = compactTpNodes.some((tp) => {
        const conn = data.connections.find((cn) => cn.to_node === tp.id || cn.from_node === tp.id)
        if (!conn) return false
        const hostId = conn.to_node === tp.id ? conn.from_node : conn.to_node
        return (nodeColMap.get(hostId) ?? 0) === c
      })

      const leftBranchPad = hasUpwardFromCol ? 42 : 0
      const tpPad = hasCompactTpInGap ? 44 : 0
      const rightBranchPad =
        downwardNetsIntoNextCol.size > 0 ? Math.max(56, downwardNetsIntoNextCol.size * 22 + 16) : 0

      const netGap = leftBranchPad + tpPad + maxNetWireLen + rightBranchPad
      colX[c + 1] = colX[c] + colWidths[c] + netGap
    }

    // 實例化所有差分節點之 LayoutNode 與 Ports
    for (let c = 0; c < numCols; c++) {
      const nodeX = colX[c]
      for (const nid of stages[c]) {
        const node = nodeById.get(nid)!
        const { width } = estimateNodeSize(node)
        const band = nodeBandMap.get(nid) ?? 0
        const { pY: nodePBaseY, nY: nodeNBaseY } = bandRailYMap.get(band) || {
          pY: pBaseY,
          nY: nBaseY,
        }

        if (isDualRailComponent(node)) {
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
            isMounted: node.is_mounted !== false && node.isMounted !== false,
            bom: node.bom,
            partdbMissing: node.partdb_missing === true,
            isTestPoint: isTestPointNode(node),
            isSinglePin: node.pins.length === 1,
          }

          if (node.role === 'series') {
            // 4-pin CMC 共模扼流圈或 4-pin 中繼穿透晶片 (如 KU100)
            const inPins = node.pins.filter((p) => p.orientation === 'left')
            const outPins = node.pins.filter((p) => p.orientation === 'right')

            const pInPin = inPins.find((p, i) => getPinPolarity(node.id, p, i) === 'p') || node.pins[0]
            const pOutPin = outPins.find((p, i) => getPinPolarity(node.id, p, i) === 'p') || node.pins[1]
            const nInPin = inPins.find((p, i) => getPinPolarity(node.id, p, i) === 'n') || node.pins[2]
            const nOutPin = outPins.find((p, i) => getPinPolarity(node.id, p, i) === 'n') || node.pins[3]

            const cmcTopPadding = 26
            const cmcBottomPadding = 16
            const actualHeight = nodeNBaseY - nodePBaseY + cmcTopPadding + cmcBottomPadding
            const nodeY = nodePBaseY - cmcTopPadding
            lNode.y = nodeY
            lNode.height = actualHeight

            if (pInPin) {
              lNode.ports.push({
                id: `${node.id}_${pInPin.pin_number}`,
                pinNumber: pInPin.pin_number,
                pinName: pInPin.pin_name,
                orientation: 'left',
                x: nodeX,
                y: nodePBaseY,
                relX: 0,
                relY: nodePBaseY - nodeY,
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
                y: nodePBaseY,
                relX: width,
                relY: nodePBaseY - nodeY,
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
                y: nodeNBaseY,
                relX: 0,
                relY: nodeNBaseY - nodeY,
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
                y: nodeNBaseY,
                relX: width,
                relY: nodeNBaseY - nodeY,
                polarity: 'n',
              })
            }
          } else {
            // 端點 IC / Connector
            const pPins = node.pins.filter((p, i) => getPinPolarity(node.id, p, i) === 'p')
            const nPins = node.pins.filter((p, i) => getPinPolarity(node.id, p, i) === 'n')

            const isStart = c === 0
            const orientation: 'left' | 'right' = isStart ? 'right' : 'left'
            const PIN_SPACING = 16
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

            const topPadding = 28
            const bottomPadding = 16
            const nodeY = Math.round(minY - topPadding)
            const nodeHeight = Math.max(54, Math.round(maxY + bottomPadding - nodeY))
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
          // 單軌 2-pin 串聯元件 (如 R63, R64, LR37, LR38, KR116 等)
          const firstPin = node.pins[0]
          const isP = firstPin ? getPinPolarity(node.id, firstPin, 0) === 'p' : true
          const targetY = isP ? nodePBaseY : nodeNBaseY
          const passiveTopPadding = 26
          const passiveBottomPadding = 14
          const passiveHeight = passiveTopPadding + passiveBottomPadding
          const nodeY = Math.round(targetY - passiveTopPadding)

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
            height: passiveHeight,
            isMounted: node.is_mounted !== false && node.isMounted !== false,
            bom: node.bom,
            partdbMissing: node.partdb_missing === true,
            isTestPoint: isTestPointNode(node),
            isSinglePin: node.pins.length === 1,
            ports: [
              {
                id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
                pinNumber: node.pins[0]?.pin_number || '1',
                pinName: node.pins[0]?.pin_name,
                orientation: 'left',
                x: nodeX,
                y: targetY,
                relX: 0,
                relY: passiveTopPadding,
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
                relY: passiveTopPadding,
                polarity: isP ? 'p' : 'n',
              },
            ],
          }
          layoutNodes.push(lNode)
          nodePositionLookup.set(node.id, lNode)
        }
      }
    }
  } else {
    // 4B. 單端信號或匯流排排版
    let curX = 36
    for (let sIdx = 0; sIdx < stages.length; sIdx++) {
      const stageIds = stages[sIdx]
      let maxStageWidth = 0
      for (const nid of stageIds) {
        const node = nodeById.get(nid)!
        const { width } = estimateNodeSize(node)
        if (width > maxStageWidth) maxStageWidth = width
      }

      for (const nid of stageIds) {
        const node = nodeById.get(nid)!
        const { width } = estimateNodeSize(node)
        const singleTopPadding = 26
        const singleBottomPadding = 14
        const singleHeight = singleTopPadding + singleBottomPadding
        const nodeY = Math.round(singleBaseY - singleTopPadding)
        const lNode: LayoutNode = {
          id: node.id,
          refDes: node.ref_des,
          category: node.category,
          role: node.role,
          partNumber: node.part_number,
          value: node.value,
          x: curX,
          y: nodeY,
          width,
          height: singleHeight,
          ports: [],
          isMounted: node.is_mounted !== false && node.isMounted !== false,
          bom: node.bom,
          isTestPoint: isTestPointNode(node),
          isSinglePin: node.pins.length === 1,
        }

        const isStart = sIdx === 0
        const isEnd = sIdx === stages.length - 1
        if (isStart) {
          lNode.ports.push({
            id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
            pinNumber: node.pins[0]?.pin_number || '1',
            pinName: node.pins[0]?.pin_name,
            orientation: 'right',
            x: curX + width,
            y: singleBaseY,
            relX: width,
            relY: singleTopPadding,
          })
        } else if (isEnd) {
          lNode.ports.push({
            id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
            pinNumber: node.pins[0]?.pin_number || '1',
            pinName: node.pins[0]?.pin_name,
            orientation: 'left',
            x: curX,
            y: singleBaseY,
            relX: 0,
            relY: singleTopPadding,
          })
        } else {
          lNode.ports.push({
            id: `${node.id}_${node.pins[0]?.pin_number || '1'}`,
            pinNumber: node.pins[0]?.pin_number || '1',
            pinName: node.pins[0]?.pin_name,
            orientation: 'left',
            x: curX,
            y: singleBaseY,
            relX: 0,
            relY: singleTopPadding,
          })
          lNode.ports.push({
            id: `${node.id}_${node.pins[1]?.pin_number || '2'}`,
            pinNumber: node.pins[1]?.pin_number || '2',
            pinName: node.pins[1]?.pin_name,
            orientation: 'right',
            x: curX + width,
            y: singleBaseY,
            relX: width,
            relY: singleTopPadding,
          })
        }

        layoutNodes.push(lNode)
        nodePositionLookup.set(node.id, lNode)
        nodeBandMap.set(node.id, 0)
      }

      const stageConns = data.connections.filter((c) => stageIds.includes(c.from_node))
      let maxNetWireLen = 36
      for (const sc of stageConns) {
        const netStr = sc.net_name || ''
        const textWidth = Math.ceil(netStr.length * 5.3)
        const requiredWireLen = textWidth + 28
        if (requiredWireLen > maxNetWireLen) {
          maxNetWireLen = requiredWireLen
        }
      }
      curX += maxStageWidth + maxNetWireLen
    }
  }

  // 5. 定位垂直支路節點 (上拉 Pull-Up 至 VCC / 接地分流 Shunt 至 GND)
  const symbols: ElectricalSymbol[] = []

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
      isMounted: node.is_mounted !== false && node.isMounted !== false,
      bom: node.bom,
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
      isMounted: node.is_mounted !== false && node.isMounted !== false,
      bom: node.bom,
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

  // 6. 建立連線 (Edges)、分支/匯流焊點 (Junction Dots)、緊湊測試點與幾何驅動之 Net 標籤 (Net Labels)
  const edges: LayoutEdge[] = []
  const junctionDots: JunctionDot[] = []
  const netLabels: NetLabel[] = []
  const horizSegments: HorizontalSegmentRecord[] = []

  // 6.1 來源端同軌多引腳匯流檢測 (Source Multi-pin Merging)
  const sourceMergeMap = new Map<string, Point>()
  for (const node of layoutNodes) {
    if (node.role !== 'terminal') continue
    const nodeBand = nodeBandMap.get(node.id) ?? 0
    const { pY: bandPY, nY: bandNY } = bandRailYMap.get(nodeBand) || { pY: pBaseY, nY: nBaseY }

    const rightPPorts = node.ports.filter((p) => p.orientation === 'right' && p.polarity === 'p')
    if (rightPPorts.length > 1) {
      const mergePoint: Point = { x: node.x + node.width + 14, y: bandPY }
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
      const mergePoint: Point = { x: node.x + node.width + 14, y: bandNY }
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

  // 6.2 目標端同軌多引腳分流檢測 (Target Multi-pin Splitting)
  const targetSplitMap = new Map<string, Point>()
  for (const node of layoutNodes) {
    if (node.role !== 'terminal') continue
    const nodeBand = nodeBandMap.get(node.id) ?? 0
    const { pY: bandPY, nY: bandNY } = bandRailYMap.get(nodeBand) || { pY: pBaseY, nY: nBaseY }

    const leftPPorts = node.ports.filter((p) => p.orientation === 'left' && p.polarity === 'p')
    if (leftPPorts.length > 1) {
      const splitY =
        nodeBand > 0
          ? Math.round(leftPPorts.reduce((sum, p) => sum + p.y, 0) / leftPPorts.length)
          : bandPY
      const splitPoint: Point = { x: node.x - 16, y: splitY }
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
      const splitY =
        nodeBand > 0
          ? Math.round(leftNPorts.reduce((sum, p) => sum + p.y, 0) / leftNPorts.length)
          : bandNY
      const splitPoint: Point = { x: node.x - 16, y: splitY }
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

  // 6.3 遍歷繪製主幹與支路連線 (預先為每個欄位間隙分配不重疊的垂直 Track 槽位)
  const drawnStemConnections = new Set<string>()
  const downwardTrackByColNet = new Map<string, number>()
  const usedDownwardXsByCol = new Map<number, Set<number>>()
  const upwardTrackByColNet = new Map<string, number>()
  const usedUpwardXsByCol = new Map<number, Set<number>>()
  const downwardDropTargetsByTrack = new Map<
    string,
    { y: number; tgtId: string; cIdx: number; polarity: 'p' | 'n' }[]
  >()

  const compactTpIdSet = new Set(compactTpNodes.map((n) => n.id))

  data.connections.forEach((conn, cIdx) => {
    if (compactTpIdSet.has(conn.to_node) || compactTpIdSet.has(conn.from_node)) return

    const srcNode = nodePositionLookup.get(conn.from_node)
    const tgtNode = nodePositionLookup.get(conn.to_node)
    if (!srcNode || !tgtNode) return

    const polarity: 'p' | 'n' = resolvePolarity(conn.rail_id, conn.net_name)
    const isN = polarity === 'n'
    const railKey = polarity

    let srcPort = srcNode.ports.find((p) => p.pinNumber === conn.from_pin)
    if (!srcPort) {
      srcPort = srcNode.ports.find(
        (p) => (p.orientation === 'right' || p.orientation === 'bottom') && p.polarity === polarity
      )
    }
    if (!srcPort) {
      srcPort = srcNode.ports.find((p) => p.orientation === 'right' || p.orientation === 'bottom')
    }

    let tgtPort = tgtNode.ports.find((p) => p.pinNumber === conn.to_pin)
    if (!tgtPort) {
      tgtPort = tgtNode.ports.find(
        (p) => (p.orientation === 'left' || p.orientation === 'top') && p.polarity === polarity
      )
    }
    if (!tgtPort) {
      tgtPort = tgtNode.ports.find((p) => p.orientation === 'left' || p.orientation === 'top')
    }

    const hasSrcMerge = sourceMergeMap.has(`${conn.from_node}#${railKey}`)
    const hasTgtSplit = targetSplitMap.has(`${conn.to_node}#${railKey}`)

    const stemKey = `${conn.from_node}->${conn.to_node}#${railKey}#${conn.net_name}`
    if ((hasSrcMerge || hasTgtSplit) && drawnStemConnections.has(stemKey)) {
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

    const isVerticalStub =
      tgtNode.role === 'pull_up' || tgtNode.role === 'shunt_ground' || tgtNode.role === 'pull_down'

    const srcBand = nodeBandMap.get(conn.from_node) ?? 0
    const tgtBand = nodeBandMap.get(conn.to_node) ?? 0
    const srcCol = nodeColMap.get(conn.from_node) ?? 0
    const tgtCol = nodeColMap.get(conn.to_node) ?? 0

    let pathD = ''

    if (isVerticalStub) {
      const junctionX = tgtPort ? tgtPort.x : (start.x + end.x) / 2
      const junctionY = start.y
      pathD = `M ${junctionX} ${junctionY} L ${end.x} ${end.y}`

      junctionDots.push({
        id: `junc_branch_${cIdx}`,
        x: junctionX,
        y: junctionY,
        polarity,
      })
    } else if (!isDiff || srcBand === tgtBand) {
      const labelWidth = Math.ceil((conn.net_name || '').length * 5.3)
      const bendX = Math.max((start.x + end.x) / 2, start.x + labelWidth + 14)
      pathD = generateOrthogonalPath(start, end, 4, bendX)

      horizSegments.push({
        netName: conn.net_name,
        polarity,
        band: srcBand,
        colStart: srcCol,
        colEnd: tgtCol,
        x1: start.x,
        x2: end.x,
        y: start.y,
        isMainBand: srcBand === 0,
      })
    } else if (tgtBand > srcBand) {
      const trackKey = `${tgtCol}#${conn.net_name}#${polarity}`
      if (!usedDownwardXsByCol.has(tgtCol)) {
        usedDownwardXsByCol.set(tgtCol, new Set())
      }
      const usedSet = usedDownwardXsByCol.get(tgtCol)!

      const colHasTargetSplit = stages[tgtCol]?.some(
        (nid) => targetSplitMap.has(`${nid}#p`) || targetSplitMap.has(`${nid}#n`)
      )

      let tapInX: number
      if (downwardTrackByColNet.has(trackKey)) {
        tapInX = downwardTrackByColNet.get(trackKey)!
      } else {
        const baseRightOffset = colHasTargetSplit ? 36 : 16
        const polOffset = isN ? 20 : 0
        tapInX = tgtNode.x - baseRightOffset - polOffset
        while (usedSet.has(tapInX) || Array.from(usedSet).some((ux) => Math.abs(ux - tapInX) < 18)) {
          tapInX -= 20
        }
        usedSet.add(tapInX)
        downwardTrackByColNet.set(trackKey, tapInX)
      }

      const trunkY = start.y
      const r = Math.min(4, Math.abs(end.x - tapInX) / 2, Math.abs(end.y - trunkY) / 2)
      const dirX = end.x >= tapInX ? 1 : -1
      pathD = [
        `M ${tapInX} ${trunkY}`,
        `L ${tapInX} ${end.y - r}`,
        `Q ${tapInX} ${end.y} ${tapInX + dirX * r} ${end.y}`,
        `L ${end.x} ${end.y}`,
      ].join(' ')

      const dotPrefix = tgtNode.role === 'series' ? 'junc_tap_in' : 'junc_tap'
      const existingOnTrack = downwardDropTargetsByTrack.get(trackKey) || []
      if (existingOnTrack.length === 0) {
        junctionDots.push({
          id: `${dotPrefix}_${cIdx}_${tgtNode.id}`,
          x: tapInX,
          y: trunkY,
          polarity,
        })
      }
      existingOnTrack.push({ y: end.y, tgtId: tgtNode.id, cIdx, polarity })
      downwardDropTargetsByTrack.set(trackKey, existingOnTrack)
    } else {
      const trackKey = `${srcCol}#${conn.net_name}#${polarity}`
      if (!usedUpwardXsByCol.has(srcCol)) {
        usedUpwardXsByCol.set(srcCol, new Set())
      }
      const usedSet = usedUpwardXsByCol.get(srcCol)!

      let tapOutX: number
      if (upwardTrackByColNet.has(trackKey)) {
        tapOutX = upwardTrackByColNet.get(trackKey)!
      } else {
        const polOffset = isN ? 20 : 0
        tapOutX = srcNode.x + srcNode.width + 16 + polOffset
        while (usedSet.has(tapOutX) || Array.from(usedSet).some((ux) => Math.abs(ux - tapOutX) < 18)) {
          tapOutX += 20
        }
        usedSet.add(tapOutX)
        upwardTrackByColNet.set(trackKey, tapOutX)
      }

      const trunkY = end.y
      const r = Math.min(4, Math.abs(tapOutX - start.x) / 2, Math.abs(start.y - trunkY) / 2)
      const dirX = end.x >= tapOutX ? 1 : -1
      pathD = [
        `M ${start.x} ${start.y}`,
        `L ${tapOutX - r} ${start.y}`,
        `Q ${tapOutX} ${start.y} ${tapOutX} ${start.y - r}`,
        `L ${tapOutX} ${trunkY + r}`,
        `Q ${tapOutX} ${trunkY} ${tapOutX + dirX * r} ${trunkY}`,
        `L ${end.x} ${trunkY}`,
      ].join(' ')

      junctionDots.push({
        id: `junc_tap_out_${cIdx}_${srcNode.id}`,
        x: tapOutX,
        y: trunkY,
        polarity,
      })

      horizSegments.push({
        netName: conn.net_name,
        polarity,
        band: tgtBand,
        colStart: srcCol,
        colEnd: tgtCol,
        x1: tapOutX,
        x2: end.x,
        y: trunkY,
        isMainBand: false,
      })
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
      isBranch: Boolean(conn.is_branch || srcBand !== tgtBand),
      polarity,
    })
  })

  for (const [trackKey, targets] of downwardDropTargetsByTrack.entries()) {
    if (targets.length <= 1) continue
    const tapInX = downwardTrackByColNet.get(trackKey)!
    const maxY = Math.max(...targets.map((t) => t.y))
    for (const t of targets) {
      if (t.y < maxY) {
        junctionDots.push({
          id: `junc_tap_mid_${t.cIdx}_${t.tgtId}`,
          x: tapInX,
          y: t.y,
          polarity: t.polarity,
        })
      }
    }
  }

  // 6.4 掛載中途緊湊型單腳測試點 (Compact Single-Pin Test Points，如 TP56 / TP57)
  const usedTpTapXs = new Set<number>()
  compactTpNodes.forEach((tpNode, tpIdx) => {
    const conn = data.connections.find((c) => c.to_node === tpNode.id || c.from_node === tpNode.id)
    if (!conn) return
    const polarity = resolvePolarity(conn.rail_id, conn.net_name)
    const isP = polarity === 'p'
    const hostNodeId = conn.to_node === tpNode.id ? conn.from_node : conn.to_node
    const hostLayout = nodePositionLookup.get(hostNodeId)

    const seg = horizSegments.find((s) => s.netName === conn.net_name && s.polarity === polarity)
    const wireY = seg ? seg.y : isP ? pBaseY : nBaseY
    let tapX = seg
      ? seg.x1 + 20
      : hostLayout
        ? hostLayout.x + hostLayout.width + 20
        : 80 + tpIdx * 40

    const dirKey = isP ? tapX : -tapX
    while (usedTpTapXs.has(dirKey)) {
      tapX += 28
    }
    usedTpTapXs.add(isP ? tapX : -tapX)

    const { width, height } = estimateNodeSize(tpNode, true)
    const stubLen = 14
    const portY = isP ? wireY - stubLen : wireY + stubLen
    const nodeX = Math.round(tapX - width / 2)
    const nodeY = isP ? wireY - stubLen - 18 : wireY + stubLen

    const lNode: LayoutNode = {
      id: tpNode.id,
      refDes: tpNode.ref_des,
      category: tpNode.category,
      role: tpNode.role,
      partNumber: tpNode.part_number,
      value: tpNode.value,
      x: nodeX,
      y: nodeY,
      width,
      height,
      isMounted: false,
      bom: tpNode.bom || 'NOBOM',
      isTestPoint: true,
      isSinglePin: true,
      tpDirection: isP ? 'up' : 'down',
      ports: [
        {
          id: `${tpNode.id}_${tpNode.pins[0]?.pin_number || '1'}`,
          pinNumber: tpNode.pins[0]?.pin_number || '1',
          pinName: tpNode.pins[0]?.pin_name,
          orientation: isP ? 'bottom' : 'top',
          x: tapX,
          y: portY,
          relX: Math.round(width / 2),
          relY: isP ? 18 : 0,
          polarity,
        },
      ],
    }
    layoutNodes.push(lNode)
    nodePositionLookup.set(tpNode.id, lNode)

    junctionDots.push({
      id: `junc_tp_${tpNode.id}`,
      x: tapX,
      y: wireY,
      polarity,
    })

    edges.push({
      id: `edge_tp_${tpNode.id}`,
      netName: conn.net_name,
      railId: conn.rail_id,
      sourceId: hostNodeId,
      targetId: tpNode.id,
      start: { x: tapX, y: wireY },
      end: { x: tapX, y: portY },
      pathD: `M ${tapX} ${wireY} L ${tapX} ${portY}`,
      isBranch: true,
      polarity,
      isTestPointStub: true,
    })
  })

  // 6.5 幾何驅動之 Net Name 標籤定位 (直接錨定於該網路最長無遮擋水平導線段正上方)
  const seenLabels = new Set<string>()
  for (let i = 0; i < horizSegments.length; i++) {
    const seg = horizSegments[i]
    if (!seg.netName || seenLabels.has(seg.netName)) continue

    const candidates = horizSegments.filter((s) => s.netName === seg.netName)
    candidates.sort((a, b) => {
      if (a.isMainBand !== b.isMainBand) return a.isMainBand ? -1 : 1
      return b.x2 - b.x1 - (a.x2 - a.x1)
    })
    const bestSeg = candidates[0]
    seenLabels.add(seg.netName)

    const minX = Math.min(bestSeg.x1, bestSeg.x2)
    const maxX = Math.max(bestSeg.x1, bestSeg.x2)
    const obstaclesX = junctionDots
      .filter((d) => Math.abs(d.y - bestSeg.y) <= 2 && d.x > minX + 4 && d.x < maxX - 4)
      .map((d) => d.x)
      .sort((a, b) => a - b)

    let subX1 = minX
    let subX2 = maxX
    if (obstaclesX.length > 0) {
      const points = [minX, ...obstaclesX, maxX]
      let bestLen = -1
      for (let k = 0; k < points.length - 1; k++) {
        const len = points[k + 1] - points[k]
        if (len > bestLen) {
          bestLen = len
          subX1 = points[k]
          subX2 = points[k + 1]
        }
      }
    }

    const labelWidth = Math.ceil(seg.netName.length * 5.3)
    netLabels.push({
      id: `lbl_${i}_${seg.netName}`,
      net: seg.netName,
      x: Math.round((subX1 + subX2) / 2),
      y: bestSeg.y - 3.5,
      width: labelWidth,
      height: 10,
      polarity: bestSeg.polarity,
    })
  }

  // 7. 計算整體 SVG 畫布邊界
  let maxX = 300
  let maxY = isDiff ? 230 : 160
  for (const n of layoutNodes) {
    if (n.x + n.width > maxX) maxX = n.x + n.width
    const extraBottom = n.partdbMissing ? 16 : 0
    if (n.y + n.height + extraBottom > maxY) maxY = n.y + n.height + extraBottom
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
