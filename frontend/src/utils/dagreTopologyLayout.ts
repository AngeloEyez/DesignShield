/**
 * @file dagreTopologyLayout.ts
 * @description 差分通道拓撲有向圖排版運算核心 (基於 Dagre 階層排版與曼哈頓直角連線)
 * 支援雙軌對齊 (P/N Dual-Rail)、元件跨軌合併、4px 圓角階梯連線與分支電氣焊點計算
 */

import dagre from 'dagre'

export interface FlowDevice {
  ref_des: string
  pin: string
  pin_name?: string
  pin_number?: string
  part_number?: string
  type?: string
}

export interface TopologyFlowStage {
  stage: 'endpoints' | 'pass_through'
  net?: string
  devices?: FlowDevice[]
  component?: string
  type?: string
  in_pin?: string
  out_pin?: string
  from_net?: string
  to_net?: string
}

export interface Point {
  x: number
  y: number
}

export interface LayoutNodePinInfo {
  refPin: string
  pinName?: string
  pinNum?: string
  throughPin?: string // 例如 "(3 ➔ 4)"
}

export interface LayoutNode {
  id: string
  refDes: string
  type: string
  isPassThrough: boolean
  partNumber?: string

  // P 極性資訊
  hasP: boolean
  pInfo?: LayoutNodePinInfo

  // N 極性資訊
  hasN: boolean
  nInfo?: LayoutNodePinInfo

  // Dagre 排版幾何屬性 (以節點左上角為基準)
  x: number
  y: number
  width: number
  height: number

  // 連接埠 (Ports) 座標
  pInPort?: Point
  pOutPort?: Point
  nInPort?: Point
  nOutPort?: Point
}

export interface LayoutEdge {
  id: string
  polarity: 'p' | 'n'
  net: string
  sourceId: string
  targetId: string
  start: Point
  end: Point
  pathD: string
  isBranch: boolean
}

export interface JunctionDot {
  id: string
  polarity: 'p' | 'n'
  x: number
  y: number
}

export interface NetLabel {
  id: string
  polarity: 'p' | 'n'
  net: string
  x: number
  y: number
  width: number
  height: number
}

export interface TopologyGraphLayout {
  width: number
  height: number
  nodes: LayoutNode[]
  edges: LayoutEdge[]
  junctionDots: JunctionDot[]
  netLabels: NetLabel[]
}

/**
 * 格式化零件與引腳在拓撲中的字串表示
 */
export function formatDeviceDisplay(dev: FlowDevice): { refPin: string; pinName?: string; pinNum?: string } {
  const pinNum = dev.pin_number || ''
  const pinNm = dev.pin_name || (dev.pin && dev.pin !== pinNum ? dev.pin : '')

  if (pinNum) {
    return {
      refPin: `${dev.ref_des}.${pinNum}`,
      pinName: pinNm || undefined,
      pinNum,
    }
  }

  if (dev.pin) {
    if (/^[A-Z]?\d+$/i.test(dev.pin)) {
      return {
        refPin: `${dev.ref_des}.${dev.pin}`,
        pinName: pinNm && pinNm !== dev.pin ? pinNm : undefined,
        pinNum: dev.pin,
      }
    }
    return {
      refPin: dev.ref_des,
      pinName: dev.pin,
    }
  }

  return {
    refPin: dev.ref_des,
  }
}

/**
 * 從原始佐證歷程正規化拓撲階層流程
 */
export function extractTopologyStages(
  evidence: Record<string, any> | undefined,
  polarity: 'p' | 'n' = 'p'
): TopologyFlowStage[] {
  if (!evidence) return []

  const flowKey = polarity === 'p' ? 'topology_flow' : 'n_topology_flow'
  if (Array.isArray(evidence[flowKey]) && evidence[flowKey].length > 0) {
    return evidence[flowKey]
  }

  const segs = polarity === 'p' ? (evidence.path_segments || []) : (evidence.n_path_segments || [])
  const endpoints = polarity === 'p' ? (evidence.p_endpoints || []) : (evidence.n_endpoints || [])
  const startNet = polarity === 'p' ? (evidence.p_net || '') : (evidence.n_net || '')

  const seenSegs = new Set<string>()
  const uniqueSegs: any[] = []
  for (const s of segs) {
    const k = `${s.from_net}|${s.pass_component}|${s.in_pin}|${s.out_pin}|${s.to_net}`
    if (!seenSegs.has(k)) {
      seenSegs.add(k)
      uniqueSegs.push(s)
    }
  }

  if (uniqueSegs.length === 0) {
    if (endpoints.length > 0) {
      return [
        {
          stage: 'endpoints',
          net: startNet,
          devices: endpoints.map((ep: any) => ({
            ref_des: ep.ref_des,
            pin: ep.pin || '',
            pin_name: ep.pin_name || (ep.pin && ep.pin !== ep.pin_number ? ep.pin : ''),
            pin_number: ep.pin_number || '',
            part_number: ep.part_number || '',
            type: ep.component_type || '',
          })),
        },
      ]
    }
    return []
  }

  const endpointsByNet: Record<string, FlowDevice[]> = {}
  for (const ep of endpoints) {
    const net = ep.connected_net || (endpoints.indexOf(ep) === 0 ? uniqueSegs[0].from_net : uniqueSegs[uniqueSegs.length - 1].to_net)
    if (!endpointsByNet[net]) {
      endpointsByNet[net] = []
    }
    endpointsByNet[net].push({
      ref_des: ep.ref_des,
      pin: ep.pin || '',
      pin_name: ep.pin_name || (ep.pin && ep.pin !== ep.pin_number ? ep.pin : ''),
      pin_number: ep.pin_number || '',
      part_number: ep.part_number || '',
      type: ep.component_type || '',
    })
  }

  const flow: TopologyFlowStage[] = []
  const visitedNets = new Set<string>()

  uniqueSegs.forEach((seg, idx) => {
    const fromNet = seg.from_net
    const toNet = seg.to_net

    if (!visitedNets.has(fromNet)) {
      visitedNets.add(fromNet)
      flow.push({
        stage: 'endpoints',
        net: fromNet,
        devices: endpointsByNet[fromNet] || [],
      })
    }

    flow.push({
      stage: 'pass_through',
      component: seg.pass_component,
      type: seg.pass_component_type || 'Passive',
      in_pin: seg.in_pin || '',
      out_pin: seg.out_pin || '',
      from_net: fromNet,
      to_net: toNet,
    })

    if (!visitedNets.has(toNet) && (idx === uniqueSegs.length - 1 || uniqueSegs[idx + 1].from_net !== toNet)) {
      visitedNets.add(toNet)
      flow.push({
        stage: 'endpoints',
        net: toNet,
        devices: endpointsByNet[toNet] || [],
      })
    }
  })

  return flow
}

/**
 * 產生曼哈頓直角階梯連線路徑 (帶有 4px 微導角)
 * 起點 -> 水平向右 -> 垂直折彎 -> 水平向右至終點
 */
export function generateOrthogonalPath(start: Point, end: Point, filletRadius = 4): string {
  const { x: x1, y: y1 } = start
  const { x: x2, y: y2 } = end

  // 若起點與終點在同一水平線上，直接直線連接
  if (Math.abs(y1 - y2) < 1) {
    return `M ${x1} ${y1} L ${x2} ${y2}`
  }

  const midX = (x1 + x2) / 2
  const dy = y2 - y1
  const r = Math.min(filletRadius, Math.abs(midX - x1) / 2, Math.abs(dy) / 2)

  if (r <= 0.5) {
    return `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`
  }

  if (dy > 0) {
    // 向下折：起點 -> 右轉向下 -> 下轉向右 -> 終點
    return `M ${x1} ${y1} L ${midX - r} ${y1} Q ${midX} ${y1} ${midX} ${y1 + r} L ${midX} ${y2 - r} Q ${midX} ${y2} ${midX + r} ${y2} L ${x2} ${y2}`
  } else {
    // 向上折：起點 -> 右轉向上 -> 上轉向右 -> 終點
    return `M ${x1} ${y1} L ${midX - r} ${y1} Q ${midX} ${y1} ${midX} ${y1 - r} L ${midX} ${y2 + r} Q ${midX} ${y2} ${midX + r} ${y2} L ${x2} ${y2}`
  }
}

/**
 * 執行差分通道拓撲排版運算 (主入口)
 */
export function computeTopologyLayout(evidence: Record<string, any> | undefined): TopologyGraphLayout {
  if (!evidence) {
    return { width: 0, height: 0, nodes: [], edges: [], junctionDots: [], netLabels: [] }
  }

  const pStages = extractTopologyStages(evidence, 'p')
  const nStages = extractTopologyStages(evidence, 'n')
  const maxStages = Math.max(pStages.length, nStages.length)

  if (maxStages === 0) {
    return { width: 0, height: 0, nodes: [], edges: [], junctionDots: [], netLabels: [] }
  }

  // 1. 初始化 Dagre 有向圖
  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: 'LR',
    align: 'UL',
    nodesep: 36,
    ranksep: 110,
    marginx: 32,
    marginy: 28,
  })
  g.setDefaultEdgeLabel(() => ({}))

  // 2. 逐階層 (Column / Rank) 建立統一節點
  const stageNodes: string[][] = []
  const nodeMap = new Map<string, Partial<LayoutNode>>()

  for (let sIdx = 0; sIdx < maxStages; sIdx++) {
    const pStage = pStages[sIdx]
    const nStage = nStages[sIdx]
    const currentStageNodeIds: string[] = []

    if (pStage?.stage === 'pass_through' || nStage?.stage === 'pass_through') {
      // 穿透性被動元件 (如 Common Mode Choke TL1)
      const refDes = pStage?.component || nStage?.component || `PT_${sIdx}`
      const type = pStage?.type || nStage?.type || 'Passive'
      const nodeId = `node_${sIdx}_${refDes}`

      const nodeData: Partial<LayoutNode> = {
        id: nodeId,
        refDes,
        type,
        isPassThrough: true,
        hasP: Boolean(pStage),
        hasN: Boolean(nStage),
        width: 154,
        height: pStage && nStage ? 78 : 50,
      }

      if (pStage) {
        nodeData.pInfo = {
          refPin: refDes,
          throughPin: pStage.in_pin && pStage.out_pin ? `(${pStage.in_pin} ➔ ${pStage.out_pin})` : undefined,
        }
      }
      if (nStage) {
        nodeData.nInfo = {
          refPin: refDes,
          throughPin: nStage.in_pin && nStage.out_pin ? `(${nStage.in_pin} ➔ ${nStage.out_pin})` : undefined,
        }
      }

      nodeMap.set(nodeId, nodeData)
      currentStageNodeIds.push(nodeId)
      g.setNode(nodeId, { width: nodeData.width, height: nodeData.height })
    } else {
      // 端點元件階層 (Endpoints: Connectors / ICs)
      const pDevices = pStage?.devices || []
      const nDevices = nStage?.devices || []

      // 依 RefDes 合併 P 與 N 端點設備
      const deviceMap = new Map<string, { pDev?: FlowDevice; nDev?: FlowDevice }>()
      for (const dev of pDevices) {
        const item = deviceMap.get(dev.ref_des) || {}
        item.pDev = dev
        deviceMap.set(dev.ref_des, item)
      }
      for (const dev of nDevices) {
        const item = deviceMap.get(dev.ref_des) || {}
        item.nDev = dev
        deviceMap.set(dev.ref_des, item)
      }

      // 如果完全沒有設備但有網路名稱，產生一個虛擬端點
      if (deviceMap.size === 0) {
        const nodeId = `node_${sIdx}_endpoint`
        const nodeData: Partial<LayoutNode> = {
          id: nodeId,
          refDes: 'Endpoint',
          type: 'Device',
          isPassThrough: false,
          hasP: Boolean(pStage),
          hasN: Boolean(nStage),
          width: 154,
          height: pStage && nStage ? 78 : 50,
        }
        nodeMap.set(nodeId, nodeData)
        currentStageNodeIds.push(nodeId)
        g.setNode(nodeId, { width: nodeData.width, height: nodeData.height })
      } else {
        for (const [refDes, { pDev, nDev }] of deviceMap.entries()) {
          const nodeId = `node_${sIdx}_${refDes}`
          const sampleDev = pDev || nDev
          const nodeData: Partial<LayoutNode> = {
            id: nodeId,
            refDes,
            type: sampleDev?.type || 'Device',
            isPassThrough: false,
            partNumber: sampleDev?.part_number,
            hasP: Boolean(pDev),
            hasN: Boolean(nDev),
            width: 154,
            height: pDev && nDev ? 78 : 50,
          }

          if (pDev) {
            const pFmt = formatDeviceDisplay(pDev)
            nodeData.pInfo = {
              refPin: pFmt.refPin,
              pinName: pFmt.pinName,
              pinNum: pFmt.pinNum,
            }
          }
          if (nDev) {
            const nFmt = formatDeviceDisplay(nDev)
            nodeData.nInfo = {
              refPin: nFmt.refPin,
              pinName: nFmt.pinName,
              pinNum: nFmt.pinNum,
            }
          }

          nodeMap.set(nodeId, nodeData)
          currentStageNodeIds.push(nodeId)
          g.setNode(nodeId, { width: nodeData.width, height: nodeData.height })
        }
      }
    }

    stageNodes.push(currentStageNodeIds)
  }

  // 3. 在相鄰階層間建立有向邊供 Dagre 排版
  for (let sIdx = 0; sIdx < stageNodes.length - 1; sIdx++) {
    const currNodes = stageNodes[sIdx]
    const nextNodes = stageNodes[sIdx + 1]
    for (const src of currNodes) {
      for (const tgt of nextNodes) {
        g.setEdge(src, tgt)
      }
    }
  }

  // 4. 執行 Dagre 階層佈局運算
  dagre.layout(g)

  // 5. 提取計算後之節點幾何屬性與 Port 座標
  const nodes: LayoutNode[] = []
  for (const [id, data] of nodeMap.entries()) {
    const dagreNode = g.node(id)
    if (!dagreNode) continue

    const width = data.width || 154
    const height = data.height || 78
    // Dagre 回傳以節點中心點 (center x, center y) 為座標，轉換為 SVG 左上角基準
    const left = dagreNode.x - width / 2
    const top = dagreNode.y - height / 2

    const isDual = data.hasP && data.hasN
    const pYOffset = isDual ? top + 34 : top + height / 2
    const nYOffset = isDual ? top + 62 : top + height / 2

    const node: LayoutNode = {
      ...(data as any),
      x: left,
      y: top,
      width,
      height,
      pInPort: data.hasP ? { x: left, y: pYOffset } : undefined,
      pOutPort: data.hasP ? { x: left + width, y: pYOffset } : undefined,
      nInPort: data.hasN ? { x: left, y: nYOffset } : undefined,
      nOutPort: data.hasN ? { x: left + width, y: nYOffset } : undefined,
    }
    nodes.push(node)
  }

  // 建立節點快速索引
  const nodeLookup = new Map<string, LayoutNode>()
  nodes.forEach((n) => nodeLookup.set(n.id, n))

  // 6. 產生具體連線 (Edges)、分支電氣焊點 (Junction Dots) 與 Net 名稱標籤
  const edges: LayoutEdge[] = []
  const junctionDots: JunctionDot[] = []
  const netLabels: NetLabel[] = []
  const seenLabels = new Set<string>()

  const polarities: ('p' | 'n')[] = ['p', 'n']

  for (const polarity of polarities) {
    const stages = polarity === 'p' ? pStages : nStages

    for (let sIdx = 0; sIdx < stageNodes.length - 1; sIdx++) {
      const currIds = stageNodes[sIdx]
      const nextIds = stageNodes[sIdx + 1]

      // 取得當前連接段之網路名稱
      const currStage = stages[sIdx]
      const nextStage = stages[sIdx + 1]
      let netName = ''
      if (currStage?.stage === 'endpoints') {
        netName = currStage.net || ''
      } else if (currStage?.stage === 'pass_through') {
        netName = currStage.to_net || ''
      } else if (nextStage?.stage === 'endpoints') {
        netName = nextStage.net || ''
      } else if (nextStage?.stage === 'pass_through') {
        netName = nextStage.from_net || ''
      }

      for (const srcId of currIds) {
        const srcNode = nodeLookup.get(srcId)
        if (!srcNode) continue

        const startPort = polarity === 'p' ? srcNode.pOutPort : srcNode.nOutPort
        if (!startPort) continue

        // 收集所有目標節點之連接埠
        const validTargets: { tgtNode: LayoutNode; endPort: Point }[] = []
        for (const tgtId of nextIds) {
          const tgtNode = nodeLookup.get(tgtId)
          if (!tgtNode) continue
          const endPort = polarity === 'p' ? tgtNode.pInPort : tgtNode.nInPort
          if (endPort) {
            validTargets.push({ tgtNode, endPort })
          }
        }

        const isBranching = validTargets.length > 1

        validTargets.forEach(({ tgtNode, endPort }, tIdx) => {
          const edgeId = `edge_${polarity}_${srcId}_${tgtNode.id}_${sIdx}`
          const pathD = generateOrthogonalPath(startPort, endPort, 4)

          edges.push({
            id: edgeId,
            polarity,
            net: netName,
            sourceId: srcId,
            targetId: tgtNode.id,
            start: startPort,
            end: endPort,
            pathD,
            isBranch: isBranching,
          })

          // 若為分支結構，在首個分叉點 (midX, start.y) 標記電氣焊點圓點 (●)
          if (isBranching && tIdx === 0) {
            const midX = (startPort.x + endPort.x) / 2
            junctionDots.push({
              id: `junc_${polarity}_${srcId}_${sIdx}`,
              polarity,
              x: midX,
              y: startPort.y,
            })
          }

          // 標註 Net 名稱標籤 (同一階層同一 Net 僅標註一次，避免視覺重複擁擠)
          const labelKey = `${polarity}_${sIdx}_${netName}`
          if (netName && !seenLabels.has(labelKey)) {
            seenLabels.add(labelKey)
            const midX = (startPort.x + endPort.x) / 2
            const labelX = (startPort.x + midX) / 2
            const labelY = startPort.y - 12
            netLabels.push({
              id: `lbl_${labelKey}`,
              polarity,
              net: netName,
              x: labelX,
              y: labelY,
              width: Math.max(70, netName.length * 6.5 + 14),
              height: 18,
            })
          }
        })
      }
    }
  }

  const gWidth = Math.max(380, (g.graph().width || 0) + 40)
  const gHeight = Math.max(160, (g.graph().height || 0) + 40)

  return {
    width: gWidth,
    height: gHeight,
    nodes,
    edges,
    junctionDots,
    netLabels,
  }
}
