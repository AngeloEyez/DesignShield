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

export interface LayoutNodePinItem {
  refPin: string
  pinName?: string
  pinNum?: string
  inPin?: string
  outPin?: string
  throughPin?: string
  yOffset: number
}

export interface LayoutNode {
  id: string
  refDes: string
  type: string
  isPassThrough: boolean
  partNumber?: string
  portDirection: 'in' | 'out' | 'both'

  // P 極性資訊 (支援多 Pin 陣列並維持向下相容)
  hasP: boolean
  pPins: LayoutNodePinItem[]
  pInfo?: LayoutNodePinInfo

  // N 極性資訊 (支援多 Pin 陣列並維持向下相容)
  hasN: boolean
  nPins: LayoutNodePinItem[]
  nInfo?: LayoutNodePinInfo

  // Dagre 排版幾何屬性 (以節點左上角為基準)
  x: number
  y: number
  width: number
  height: number

  // 連接埠 (Ports) 座標 (包含單一主埠與多連接埠列表)
  pInPort?: Point
  pOutPort?: Point
  nInPort?: Point
  nOutPort?: Point
  pInPorts?: Point[]
  pOutPorts?: Point[]
  nInPorts?: Point[]
  nOutPorts?: Point[]
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
    const rawFlow: TopologyFlowStage[] = evidence[flowKey]
    const hasAnyRealDevice = rawFlow.some(
      (s) => s.stage === 'endpoints' && Array.isArray(s.devices) && s.devices.length > 0
    )

    // 過濾掉鏈路中「無任何設備」的中繼 Net 階層 (若鏈路具備實體設備，杜絕在任何位置插入多餘的虛擬 Endpoint 節點)
    return rawFlow.filter((stage) => {
      if (stage.stage === 'endpoints') {
        const hasDevices = Array.isArray(stage.devices) && stage.devices.length > 0
        if (!hasDevices && hasAnyRealDevice) {
          return false
        }
      }
      return true
    })
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
      const devs = endpointsByNet[fromNet] || []
      // 只有在首端 (idx === 0) 或有實體設備時才建立 endpoints stage
      if (idx === 0 || devs.length > 0) {
        flow.push({
          stage: 'endpoints',
          net: fromNet,
          devices: devs,
        })
      }
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
      const devs = endpointsByNet[toNet] || []
      // 只有在末端 (idx === uniqueSegs.length - 1) 或有實體設備時才建立 endpoints stage
      if (idx === uniqueSegs.length - 1 || devs.length > 0) {
        flow.push({
          stage: 'endpoints',
          net: toNet,
          devices: devs,
        })
      }
    }
  })

  return flow
}

/**
 * 產生曼哈頓直角階梯連線路徑 (帶有 4px 微導角)
 * 起點 -> 水平向右 -> 垂直折彎 -> 水平向右至終點
 * 支援指定自訂 turnX 折轉點，以實現多軌平行避讓與防重疊
 */
export function generateOrthogonalPath(
  start: Point,
  end: Point,
  filletRadius = 4,
  turnX?: number
): string {
  const { x: x1, y: y1 } = start
  const { x: x2, y: y2 } = end

  // 若起點與終點在同一水平線上，直接直線連接
  if (Math.abs(y1 - y2) < 1) {
    return `M ${x1} ${y1} L ${x2} ${y2}`
  }

  // 若有指定 turnX，使用指定位置；否則預設取中點
  const tx = turnX !== undefined ? turnX : (x1 + x2) / 2
  const dy = y2 - y1

  // 如果起點就在 turnX 上 (如 T-tap 分支垂直探出連線)，起點直接垂直出發，在目標轉折處計算單轉角圓弧
  if (Math.abs(tx - x1) < 1) {
    const r = Math.min(filletRadius, Math.abs(x2 - tx) / 2, Math.abs(dy) / 2)
    if (r <= 0.5) {
      return `M ${x1} ${y1} L ${tx} ${y2} L ${x2} ${y2}`
    }
    if (dy > 0) {
      // 垂直向下 -> 轉向右
      return `M ${x1} ${y1} L ${tx} ${y2 - r} Q ${tx} ${y2} ${tx + r} ${y2} L ${x2} ${y2}`
    } else {
      // 垂直向上 -> 轉向右
      return `M ${x1} ${y1} L ${tx} ${y2 + r} Q ${tx} ${y2} ${tx + r} ${y2} L ${x2} ${y2}`
    }
  }

  // 如果終點就在 turnX 上 (如多 Pin 匯流垂直到達交會點)，起點水平出發，在 turnX 轉折處垂直進入終點
  if (Math.abs(tx - x2) < 1) {
    const r = Math.min(filletRadius, Math.abs(tx - x1) / 2, Math.abs(dy) / 2)
    if (r <= 0.5) {
      return `M ${x1} ${y1} L ${tx} ${y1} L ${tx} ${y2}`
    }
    if (dy > 0) {
      // 水平向右 -> 轉向下進入終點
      return `M ${x1} ${y1} L ${tx - r} ${y1} Q ${tx} ${y1} ${tx} ${y1 + r} L ${tx} ${y2}`
    } else {
      // 水平向右 -> 轉向上進入終點
      return `M ${x1} ${y1} L ${tx - r} ${y1} Q ${tx} ${y1} ${tx} ${y1 - r} L ${tx} ${y2}`
    }
  }

  const r = Math.min(filletRadius, Math.abs(tx - x1) / 2, Math.abs(x2 - tx) / 2, Math.abs(dy) / 2)

  if (r <= 0.5) {
    return `M ${x1} ${y1} L ${tx} ${y1} L ${tx} ${y2} L ${x2} ${y2}`
  }

  if (dy > 0) {
    // 向下折：起點 -> 右轉向下 -> 下轉向右 -> 終點
    return `M ${x1} ${y1} L ${tx - r} ${y1} Q ${tx} ${y1} ${tx} ${y1 + r} L ${tx} ${y2 - r} Q ${tx} ${y2} ${tx + r} ${y2} L ${x2} ${y2}`
  } else {
    // 向上折：起點 -> 右轉向上 -> 上轉向右 -> 終點
    return `M ${x1} ${y1} L ${tx - r} ${y1} Q ${tx} ${y1} ${tx} ${y1 - r} L ${tx} ${y2 + r} Q ${tx} ${y2} ${tx + r} ${y2} L ${x2} ${y2}`
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

  // 統計所有階層間出現的最長 Net Name，動態給予充足且緊湊的 ranksep
  let maxNetLen = 0
  for (const s of [...pStages, ...nStages]) {
    maxNetLen = Math.max(
      maxNetLen,
      s.net?.length || 0,
      s.from_net?.length || 0,
      s.to_net?.length || 0
    )
  }

  // 每個 Net Name 字元在 text-[8.5px] 約佔 4.9px
  // 檢查所有階層是否有任何分支 (某階層有多個設備，如 TU2 + P72)
  let hasBranch = false
  for (let sIdx = 0; sIdx < maxStages - 1; sIdx++) {
    const nextP = pStages[sIdx + 1]?.devices?.length ?? 0
    const nextN = nStages[sIdx + 1]?.devices?.length ?? 0
    if (nextP > 1 || nextN > 1) {
      hasBranch = true
      break
    }
  }

  // 若無分支 (純直行鏈路)，保留 42px 充足轉折緩衝空間，保證階梯折線轉折點落在文字結尾右側且不重疊；有分支則留 76px 予 T-tap 錯開避讓與分流
  const rankSepBuffer = hasBranch ? 76 : 42
  const minRankSep = hasBranch ? 124 : 84
  const dynamicRankSep = Math.max(minRankSep, Math.ceil(maxNetLen * 4.9 + rankSepBuffer))

  // 1. 初始化 Dagre 有向圖
  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: 'LR',
    align: 'UL',
    nodesep: 20,
    ranksep: dynamicRankSep,
    marginx: 24,
    marginy: 20,
  })
  g.setDefaultEdgeLabel(() => ({}))

  // 計算符合內部文字需求之緊湊節點寬高 (依引腳數量動態擴展高度，不重複節點編號)
  const calcNodeDimensions = (
    refDes: string,
    pPins: LayoutNodePinItem[],
    nPins: LayoutNodePinItem[]
  ): { width: number; height: number } => {
    const totalPins = pPins.length + nPins.length
    // 若無引腳預設 36px/52px；每個引腳行佔高 16px，頂部 header 佔高 18px，底留 6px
    const height = totalPins <= 1 ? 38 : Math.max(52, totalPins * 16 + 18)

    const getPinChars = (pin: LayoutNodePinItem) => {
      if (pin.throughPin) {
        return (pin.inPin?.length || 1) + (pin.outPin?.length || 1) + 4
      }
      const numLen = pin.pinNum ? pin.pinNum.length : 0
      const nameLen = pin.pinName ? pin.pinName.length + 1 : 0
      return numLen + nameLen
    }

    const refDesChars = refDes.length
    const maxPinChars = Math.max(0, ...pPins.map(getPinChars), ...nPins.map(getPinChars))

    // 在 SVG 內 text-[10px] bold 約 5.8px/字元，text-[9px] mono 約 5.2px/字元
    const maxTextWidth = Math.max(
      refDesChars * 5.8,
      maxPinChars * 5.2
    )

    // 左右 padding 各 8px，總計 16px；最小寬度設為 62px
    const width = Math.max(62, Math.ceil(maxTextWidth + 18))
    return { width, height }
  }

  // 2. 逐階層 (Column / Rank) 建立統一節點
  const stageNodes: string[][] = []
  const nodeMap = new Map<string, Partial<LayoutNode>>()

  for (let sIdx = 0; sIdx < maxStages; sIdx++) {
    const pStage = pStages[sIdx]
    const nStage = nStages[sIdx]
    const currentStageNodeIds: string[] = []

    // 判定節點的 Port 預設朝向 (第 0 階為輸出 out，最後一階為輸入 in，穿透元件為 both)
    const portDir: 'in' | 'out' | 'both' =
      sIdx === 0 ? 'out' : (sIdx === maxStages - 1 ? 'in' : 'both')

    if (pStage?.stage === 'pass_through' || nStage?.stage === 'pass_through') {
      const pComp = pStage?.component
      const nComp = nStage?.component
      const isShared = Boolean(pComp && nComp && pComp === nComp)

      if (isShared && pComp) {
        // 情況 A：P 軌與 N 軌共用同一顆零件 (如 Common Mode Choke TL1)
        const refDes = pComp
        const type = pStage?.type || nStage?.type || 'Passive'
        const nodeId = `node_${sIdx}_${refDes}`

        const pPins: LayoutNodePinItem[] = pStage ? [{
          refPin: refDes,
          inPin: pStage.in_pin,
          outPin: pStage.out_pin,
          throughPin: pStage.in_pin && pStage.out_pin ? `(${pStage.in_pin} ➔ ${pStage.out_pin})` : undefined,
          yOffset: 24,
        }] : []

        const nPins: LayoutNodePinItem[] = nStage ? [{
          refPin: refDes,
          inPin: nStage.in_pin,
          outPin: nStage.out_pin,
          throughPin: nStage.in_pin && nStage.out_pin ? `(${nStage.in_pin} ➔ ${nStage.out_pin})` : undefined,
          yOffset: 40,
        }] : []

        const { width, height } = calcNodeDimensions(refDes, pPins, nPins)

        const nodeData: Partial<LayoutNode> = {
          id: nodeId,
          refDes,
          type,
          isPassThrough: true,
          portDirection: 'both',
          hasP: true,
          hasN: true,
          pPins,
          nPins,
          pInfo: pPins[0] ? {
            refPin: pPins[0].refPin,
            throughPin: pPins[0].throughPin,
          } : undefined,
          nInfo: nPins[0] ? {
            refPin: nPins[0].refPin,
            throughPin: nPins[0].throughPin,
          } : undefined,
          width,
          height: height || 52,
        }

        nodeMap.set(nodeId, nodeData)
        currentStageNodeIds.push(nodeId)
        g.setNode(nodeId, { width: nodeData.width, height: nodeData.height })
      } else {
        // 情況 B：P 軌與 N 軌為獨立分立元件 (如 P 端為 TC13，N 端為 TC14)
        if (pStage && pComp) {
          const refDes = pComp
          const type = pStage.type || 'Passive'
          const nodeId = `node_${sIdx}_${refDes}_P`

          const pPins: LayoutNodePinItem[] = [{
            refPin: refDes,
            inPin: pStage.in_pin,
            outPin: pStage.out_pin,
            throughPin: pStage.in_pin && pStage.out_pin ? `(${pStage.in_pin} ➔ ${pStage.out_pin})` : undefined,
            yOffset: 20,
          }]

          const { width } = calcNodeDimensions(refDes, pPins, [])

          const nodeData: Partial<LayoutNode> = {
            id: nodeId,
            refDes,
            type,
            isPassThrough: true,
            portDirection: 'both',
            hasP: true,
            hasN: false,
            pPins,
            nPins: [],
            pInfo: {
              refPin: pPins[0].refPin,
              throughPin: pPins[0].throughPin,
            },
            width,
            height: 38,
          }

          nodeMap.set(nodeId, nodeData)
          currentStageNodeIds.push(nodeId)
          g.setNode(nodeId, { width: nodeData.width, height: nodeData.height })
        }

        if (nStage && nComp) {
          const refDes = nComp
          const type = nStage.type || 'Passive'
          const nodeId = `node_${sIdx}_${refDes}_N`

          const nPins: LayoutNodePinItem[] = [{
            refPin: refDes,
            inPin: nStage.in_pin,
            outPin: nStage.out_pin,
            throughPin: nStage.in_pin && nStage.out_pin ? `(${nStage.in_pin} ➔ ${nStage.out_pin})` : undefined,
            yOffset: 20,
          }]

          const { width } = calcNodeDimensions(refDes, [], nPins)

          const nodeData: Partial<LayoutNode> = {
            id: nodeId,
            refDes,
            type,
            isPassThrough: true,
            portDirection: 'both',
            hasP: false,
            hasN: true,
            pPins: [],
            nPins,
            nInfo: {
              refPin: nPins[0].refPin,
              throughPin: nPins[0].throughPin,
            },
            width,
            height: 38,
          }

          nodeMap.set(nodeId, nodeData)
          currentStageNodeIds.push(nodeId)
          g.setNode(nodeId, { width: nodeData.width, height: nodeData.height })
        }
      }
    } else {
      // 端點元件階層 (Endpoints: Connectors / ICs)
      const pDevices = pStage?.devices || []
      const nDevices = nStage?.devices || []

      // 依 RefDes 合併 P 與 N 端點設備列表 (允許多 Pin，杜絕覆蓋丟失！)
      const deviceMap = new Map<string, { pDevs: FlowDevice[]; nDevs: FlowDevice[] }>()
      for (const dev of pDevices) {
        const item = deviceMap.get(dev.ref_des) || { pDevs: [], nDevs: [] }
        item.pDevs.push(dev)
        deviceMap.set(dev.ref_des, item)
      }
      for (const dev of nDevices) {
        const item = deviceMap.get(dev.ref_des) || { pDevs: [], nDevs: [] }
        item.nDevs.push(dev)
        deviceMap.set(dev.ref_des, item)
      }

      // 如果完全沒有設備但有網路名稱，產生一個虛擬端點
      if (deviceMap.size === 0) {
        const nodeId = `node_${sIdx}_endpoint`
        const pPins: LayoutNodePinItem[] = Boolean(pStage) ? [{ refPin: 'Endpoint', pinNum: 'P+', yOffset: 24 }] : []
        const nPins: LayoutNodePinItem[] = Boolean(nStage) ? [{ refPin: 'Endpoint', pinNum: 'N-', yOffset: 40 }] : []
        const { width, height } = calcNodeDimensions('Endpoint', pPins, nPins)
        const nodeData: Partial<LayoutNode> = {
          id: nodeId,
          refDes: 'Endpoint',
          type: 'Device',
          isPassThrough: false,
          portDirection: portDir,
          hasP: Boolean(pStage),
          hasN: Boolean(nStage),
          pPins,
          nPins,
          width,
          height,
        }
        nodeMap.set(nodeId, nodeData)
        currentStageNodeIds.push(nodeId)
        g.setNode(nodeId, { width: nodeData.width, height: nodeData.height })
      } else {
        for (const [refDes, { pDevs, nDevs }] of deviceMap.entries()) {
          const nodeId = `node_${sIdx}_${refDes}`
          const sampleDev = pDevs[0] || nDevs[0]

          const pPins: LayoutNodePinItem[] = pDevs.map((dev) => {
            const fmt = formatDeviceDisplay(dev)
            return {
              refPin: fmt.refPin,
              pinName: fmt.pinName,
              pinNum: fmt.pinNum || dev.pin || '',
              yOffset: 0,
            }
          })

          const nPins: LayoutNodePinItem[] = nDevs.map((dev) => {
            const fmt = formatDeviceDisplay(dev)
            return {
              refPin: fmt.refPin,
              pinName: fmt.pinName,
              pinNum: fmt.pinNum || dev.pin || '',
              yOffset: 0,
            }
          })

          const { width, height } = calcNodeDimensions(refDes, pPins, nPins)

          const nodeData: Partial<LayoutNode> = {
            id: nodeId,
            refDes,
            type: sampleDev?.type || 'Device',
            isPassThrough: false,
            portDirection: portDir,
            partNumber: sampleDev?.part_number,
            hasP: pPins.length > 0,
            hasN: nPins.length > 0,
            pPins,
            nPins,
            pInfo: pPins[0] ? {
              refPin: pPins[0].refPin,
              pinName: pPins[0].pinName,
              pinNum: pPins[0].pinNum,
            } : undefined,
            nInfo: nPins[0] ? {
              refPin: nPins[0].refPin,
              pinName: nPins[0].pinName,
              pinNum: nPins[0].pinNum,
            } : undefined,
            width,
            height,
          }

          nodeMap.set(nodeId, nodeData)
          currentStageNodeIds.push(nodeId)
          g.setNode(nodeId, { width: nodeData.width, height: nodeData.height })
        }
      }
    }

    stageNodes.push(currentStageNodeIds)
  }

  // 3. 在相鄰階層間建立有向邊供 Dagre 排版 (依極性相符精確連邊，P 連 P，N 連 N，維持平行軌道)
  for (let sIdx = 0; sIdx < stageNodes.length - 1; sIdx++) {
    const currNodes = stageNodes[sIdx]
    const nextNodes = stageNodes[sIdx + 1]
    for (const src of currNodes) {
      for (const tgt of nextNodes) {
        const srcData = nodeMap.get(src)
        const tgtData = nodeMap.get(tgt)
        const matchP = Boolean(srcData?.hasP && tgtData?.hasP)
        const matchN = Boolean(srcData?.hasN && tgtData?.hasN)
        if (matchP || matchN || (!srcData?.hasP && !srcData?.hasN)) {
          g.setEdge(src, tgt)
        }
      }
    }
  }

  // 4. 執行 Dagre 階層佈局運算
  dagre.layout(g)

  // 5. 提取計算後之節點幾何屬性與 Port 座標 (多 Pin 各自定位)
  const nodes: LayoutNode[] = []
  for (const [id, data] of nodeMap.entries()) {
    const dagreNode = g.node(id)
    if (!dagreNode) continue

    const width = data.width || 62
    const height = data.height || 52
    const left = dagreNode.x - width / 2
    const top = dagreNode.y - height / 2

    const pPins = data.pPins || []
    const nPins = data.nPins || []

    let pinY = 24
    for (const pin of pPins) {
      pin.yOffset = pinY
      pinY += 16
    }
    for (const pin of nPins) {
      pin.yOffset = pinY
      pinY += 16
    }

    const pInPorts = pPins.map((p) => ({ x: left, y: top + p.yOffset - 1 }))
    const pOutPorts = pPins.map((p) => ({ x: left + width, y: top + p.yOffset - 1 }))
    const nInPorts = nPins.map((p) => ({ x: left, y: top + p.yOffset - 1 }))
    const nOutPorts = nPins.map((p) => ({ x: left + width, y: top + p.yOffset - 1 }))

    const node: LayoutNode = {
      ...(data as any),
      x: left,
      y: top,
      width,
      height,
      pPins,
      nPins,
      pInPorts,
      pOutPorts,
      nInPorts,
      nOutPorts,
      pInPort: pInPorts[0],
      pOutPort: pOutPorts[0],
      nInPort: nInPorts[0],
      nOutPort: nOutPorts[0],
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

  for (let sIdx = 0; sIdx < stageNodes.length - 1; sIdx++) {
    const currIds = stageNodes[sIdx]
    const nextIds = stageNodes[sIdx + 1]

    // 取得當前連接段之網路名稱
    const pCurrStage = pStages[sIdx]
    const pNextStage = pStages[sIdx + 1]
    let pNetName = ''
    if (pCurrStage?.stage === 'endpoints') {
      pNetName = pCurrStage.net || ''
    } else if (pCurrStage?.stage === 'pass_through') {
      pNetName = pCurrStage.to_net || ''
    } else if (pNextStage?.stage === 'endpoints') {
      pNetName = pNextStage.net || ''
    } else if (pNextStage?.stage === 'pass_through') {
      pNetName = pNextStage.from_net || ''
    }

    const nCurrStage = nStages[sIdx]
    const nNextStage = nStages[sIdx + 1]
    let nNetName = ''
    if (nCurrStage?.stage === 'endpoints') {
      nNetName = nCurrStage.net || ''
    } else if (nCurrStage?.stage === 'pass_through') {
      nNetName = nCurrStage.to_net || ''
    } else if (nNextStage?.stage === 'endpoints') {
      nNetName = nNextStage.net || ''
    } else if (nNextStage?.stage === 'pass_through') {
      nNetName = nNextStage.from_net || ''
    }

    for (const srcId of currIds) {
      const srcNode = nodeLookup.get(srcId)
      if (!srcNode) continue

      // 判斷來源端是否有多個 Pin 需要在節點右側先行匯流 (如 TJ1 擁有 2 個 P pin / 2 個 N pin)
      const hasMultiPOut = (srcNode.pOutPorts?.length ?? 0) > 1
      const hasMultiNOut = (srcNode.nOutPorts?.length ?? 0) > 1

      // 匯流交會點 X 座標：節點右側 14px，Y 座標取所有引腳垂直中心 (僅在多引腳時計算)
      const pOrigin = hasMultiPOut
        ? {
            x: srcNode.x + srcNode.width + 14,
            y: srcNode.pOutPorts!.reduce((sum, p) => sum + p.y, 0) / srcNode.pOutPorts!.length,
          }
        : srcNode.pOutPort

      const nOrigin = hasMultiNOut
        ? {
            x: srcNode.x + srcNode.width + 14,
            y: srcNode.nOutPorts!.reduce((sum, p) => sum + p.y, 0) / srcNode.nOutPorts!.length,
          }
        : srcNode.nOutPort

      // 若有複數 P 引腳，繪製各引腳至匯流點的走線並打上焊點 (端點接在 port 上；焊點精確打在兩線/多線交會處 pOrigin)
      if (hasMultiPOut && pOrigin) {
        srcNode.pOutPorts!.forEach((port, pIdx) => {
          const pathD = Math.abs(port.y - pOrigin.y) < 1
            ? `M ${port.x} ${port.y} L ${pOrigin.x} ${port.y}`
            : generateOrthogonalPath(port, pOrigin, 3, pOrigin.x)

          edges.push({
            id: `merge_p_${srcId}_pin_${pIdx}_${sIdx}`,
            polarity: 'p',
            net: pNetName,
            sourceId: srcId,
            targetId: srcId,
            start: port,
            end: pOrigin,
            pathD,
            isBranch: false,
          })
        })

        junctionDots.push({
          id: `merge_junc_p_${srcId}_${sIdx}`,
          polarity: 'p',
          x: pOrigin.x,
          y: pOrigin.y,
        })
      }

      // 若有複數 N 引腳，繪製各引腳至匯流點的走線並打上焊點 (焊點精確打在兩線/多線交會處 nOrigin)
      if (hasMultiNOut && nOrigin) {
        srcNode.nOutPorts!.forEach((port, nIdx) => {
          const pathD = Math.abs(port.y - nOrigin.y) < 1
            ? `M ${port.x} ${port.y} L ${nOrigin.x} ${port.y}`
            : generateOrthogonalPath(port, nOrigin, 3, nOrigin.x)

          edges.push({
            id: `merge_n_${srcId}_pin_${nIdx}_${sIdx}`,
            polarity: 'n',
            net: nNetName,
            sourceId: srcId,
            targetId: srcId,
            start: port,
            end: nOrigin,
            pathD,
            isBranch: false,
          })
        })

        junctionDots.push({
          id: `merge_junc_n_${srcId}_${sIdx}`,
          polarity: 'n',
          x: nOrigin.x,
          y: nOrigin.y,
        })
      }

      // 標註 Net 名稱標籤 (緊貼來源端點/匯流點右側 6px，由左至右書寫，不遮擋節點)
      if (pOrigin && pNetName) {
        const pLabelKey = `p_${sIdx}_${pNetName}`
        if (!seenLabels.has(pLabelKey)) {
          seenLabels.add(pLabelKey)
          netLabels.push({
            id: `lbl_${pLabelKey}`,
            polarity: 'p',
            net: pNetName,
            x: pOrigin.x + 6,
            y: pOrigin.y - 3.5,
            width: Math.ceil(pNetName.length * 4.9),
            height: 10,
          })
        }
      }

      if (nOrigin && nNetName) {
        const nLabelKey = `n_${sIdx}_${nNetName}`
        if (!seenLabels.has(nLabelKey)) {
          seenLabels.add(nLabelKey)
          netLabels.push({
            id: `lbl_${nLabelKey}`,
            polarity: 'n',
            net: nNetName,
            x: nOrigin.x + 6,
            y: nOrigin.y - 3.5,
            width: Math.ceil(nNetName.length * 4.9),
            height: 10,
          })
        }
      }

      // 收集目標並計算各目標分流點 (採 P/N 極性獨立分組，杜絕跨軌混雜與 N 軌斷線)
      interface PolarityTargetInfo {
        tgtNode: LayoutNode
        targetPoint: Point
        hasMulti: boolean
        inPorts: Point[]
      }

      const pTargetList: PolarityTargetInfo[] = []
      const nTargetList: PolarityTargetInfo[] = []

      for (const tgtId of nextIds) {
        const tgtNode = nodeLookup.get(tgtId)
        if (!tgtNode) continue

        // 收集 P 軌有效目標
        if (tgtNode.hasP && (tgtNode.pInPort || (tgtNode.pInPorts?.length ?? 0) > 0)) {
          const hasMultiP = (tgtNode.pInPorts?.length ?? 0) > 1
          const pY = hasMultiP
            ? tgtNode.pInPorts!.reduce((sum, p) => sum + p.y, 0) / tgtNode.pInPorts!.length
            : tgtNode.pInPort!.y
          const targetPoint: Point = {
            x: hasMultiP ? tgtNode.x - 14 : tgtNode.pInPort!.x,
            y: pY,
          }
          pTargetList.push({
            tgtNode,
            targetPoint,
            hasMulti: hasMultiP,
            inPorts: tgtNode.pInPorts || [],
          })
        }

        // 收集 N 軌有效目標
        if (tgtNode.hasN && (tgtNode.nInPort || (tgtNode.nInPorts?.length ?? 0) > 0)) {
          const hasMultiN = (tgtNode.nInPorts?.length ?? 0) > 1
          const nY = hasMultiN
            ? tgtNode.nInPorts!.reduce((sum, p) => sum + p.y, 0) / tgtNode.nInPorts!.length
            : tgtNode.nInPort!.y
          const targetPoint: Point = {
            x: hasMultiN ? tgtNode.x - 14 : tgtNode.nInPort!.x,
            y: nY,
          }
          nTargetList.push({
            tgtNode,
            targetPoint,
            hasMulti: hasMultiN,
            inPorts: tgtNode.nInPorts || [],
          })
        }
      }

      // 1. 繪製各目標節點內部的多 Pin 分流 (Split)
      for (const t of pTargetList) {
        if (t.hasMulti) {
          const splitKey = `split_p_${t.tgtNode.id}_${sIdx}`
          if (!seenLabels.has(splitKey)) {
            seenLabels.add(splitKey)
            t.inPorts.forEach((port, pIdx) => {
              const splitPath = Math.abs(port.y - t.targetPoint.y) < 1
                ? `M ${t.targetPoint.x} ${t.targetPoint.y} L ${port.x} ${port.y}`
                : generateOrthogonalPath(t.targetPoint, port, 3, t.targetPoint.x)

              edges.push({
                id: `split_p_${t.tgtNode.id}_pin_${pIdx}_${sIdx}`,
                polarity: 'p',
                net: pNetName,
                sourceId: t.tgtNode.id,
                targetId: t.tgtNode.id,
                start: t.targetPoint,
                end: port,
                pathD: splitPath,
                isBranch: false,
              })
            })

            junctionDots.push({
              id: `split_junc_p_${t.tgtNode.id}_${sIdx}`,
              polarity: 'p',
              x: t.targetPoint.x,
              y: t.targetPoint.y,
            })
          }
        }
      }

      for (const t of nTargetList) {
        if (t.hasMulti) {
          const splitKey = `split_n_${t.tgtNode.id}_${sIdx}`
          if (!seenLabels.has(splitKey)) {
            seenLabels.add(splitKey)
            t.inPorts.forEach((port, nIdx) => {
              const splitPath = Math.abs(port.y - t.targetPoint.y) < 1
                ? `M ${t.targetPoint.x} ${t.targetPoint.y} L ${port.x} ${port.y}`
                : generateOrthogonalPath(t.targetPoint, port, 3, t.targetPoint.x)

              edges.push({
                id: `split_n_${t.tgtNode.id}_pin_${nIdx}_${sIdx}`,
                polarity: 'n',
                net: nNetName,
                sourceId: t.tgtNode.id,
                targetId: t.tgtNode.id,
                start: t.targetPoint,
                end: port,
                pathD: splitPath,
                isBranch: false,
              })
            })

            junctionDots.push({
              id: `split_junc_n_${t.tgtNode.id}_${sIdx}`,
              polarity: 'n',
              x: t.targetPoint.x,
              y: t.targetPoint.y,
            })
          }
        }
      }

      // 2. P 軌連線繪製 (極性完全隔離)
      if (pOrigin && pTargetList.length > 0) {
        const sortedPTargets = [...pTargetList].sort((a, b) => {
          return Math.abs(a.targetPoint.y - pOrigin.y) - Math.abs(b.targetPoint.y - pOrigin.y)
        })

        const pPrimary = sortedPTargets[0]
        const pBranches = sortedPTargets.slice(1)

        const srcRight = pOrigin.x
        const primaryLeft = pPrimary.targetPoint.x
        const pNetChars = pNetName.length
        const pTextWidth = Math.ceil(pNetChars * 4.9)
        // 嚴格轉折下限：轉折點必須在 Net 文字結束點右側至少 12px
        const minTurnX = srcRight + 6 + pTextWidth + 12

        const maxTapX = primaryLeft - 20
        const safeMidTapX = maxTapX > minTurnX ? (minTurnX + maxTapX) / 2 : minTurnX
        const pBranchTapXs: number[] = []

        // P 軌分支繪製 (若有分支)
        for (let bIdx = 0; bIdx < pBranches.length; bIdx++) {
          const br = pBranches[bIdx]
          const isDownward = br.targetPoint.y > pOrigin.y
          let tapX = isDownward ? safeMidTapX + 10 + bIdx * 16 : safeMidTapX - 10 - bIdx * 16
          tapX = Math.max(minTurnX, Math.min(tapX, maxTapX))
          pBranchTapXs.push(tapX)

          const tapPoint: Point = { x: tapX, y: pOrigin.y }
          const branchPath = generateOrthogonalPath(tapPoint, br.targetPoint, 4, tapX)

          edges.push({
            id: `edge_p_${srcId}_${br.tgtNode.id}_${sIdx}`,
            polarity: 'p',
            net: pNetName,
            sourceId: srcId,
            targetId: br.tgtNode.id,
            start: tapPoint,
            end: br.targetPoint,
            pathD: branchPath,
            isBranch: true,
          })

          junctionDots.push({
            id: `junc_p_${srcId}_${br.tgtNode.id}_${sIdx}`,
            polarity: 'p',
            x: tapX,
            y: pOrigin.y,
          })
        }

        // P 軌主幹繪製 (單一路徑直達主目標)
        // 主幹階梯轉折點：嚴格在所有分支 tapX 右側，確保主幹在分支交會處為水平穿過
        const maxBranchTapX = pBranchTapXs.length > 0
          ? Math.max(...pBranchTapXs)
          : minTurnX
        const trunkTurnX = Math.min(
          primaryLeft - 10,
          Math.max(maxBranchTapX + 10, (maxBranchTapX + primaryLeft) / 2)
        )

        const isStraight = Math.abs(pPrimary.targetPoint.y - pOrigin.y) < 1.5
        const pathD = isStraight
          ? `M ${pOrigin.x} ${pOrigin.y} L ${pPrimary.targetPoint.x} ${pPrimary.targetPoint.y}`
          : generateOrthogonalPath(pOrigin, pPrimary.targetPoint, 4, trunkTurnX)

        edges.push({
          id: `edge_p_${srcId}_${pPrimary.tgtNode.id}_${sIdx}`,
          polarity: 'p',
          net: pNetName,
          sourceId: srcId,
          targetId: pPrimary.tgtNode.id,
          start: pOrigin,
          end: pPrimary.targetPoint,
          pathD,
          isBranch: false,
        })
      }

      // 3. N 軌連線繪製 (極性完全隔離)
      if (nOrigin && nTargetList.length > 0) {
        const sortedNTargets = [...nTargetList].sort((a, b) => {
          return Math.abs(a.targetPoint.y - nOrigin.y) - Math.abs(b.targetPoint.y - nOrigin.y)
        })

        const nPrimary = sortedNTargets[0]
        const nBranches = sortedNTargets.slice(1)

        const srcRight = nOrigin.x
        const primaryLeft = nPrimary.targetPoint.x
        const nNetChars = nNetName.length
        const nTextWidth = Math.ceil(nNetChars * 4.9)
        const minTurnX = srcRight + 6 + nTextWidth + 12
        const maxTapX = primaryLeft - 20
        const safeMidTapX = maxTapX > minTurnX ? (minTurnX + maxTapX) / 2 : minTurnX
        const nBranchTapXs: number[] = []

        // N 軌分支繪製 (若有分支)
        for (let bIdx = 0; bIdx < nBranches.length; bIdx++) {
          const br = nBranches[bIdx]
          const isDownward = br.targetPoint.y > nOrigin.y
          // 與 P 軌分支避讓錯開 (向下走向下方元件時，N 軌提前在左側轉折)
          let tapX = isDownward ? safeMidTapX - 10 - bIdx * 16 : safeMidTapX + 10 + bIdx * 16
          tapX = Math.max(minTurnX, Math.min(tapX, maxTapX))
          nBranchTapXs.push(tapX)

          const tapPoint: Point = { x: tapX, y: nOrigin.y }
          const branchPath = generateOrthogonalPath(tapPoint, br.targetPoint, 4, tapX)

          edges.push({
            id: `edge_n_${srcId}_${br.tgtNode.id}_${sIdx}`,
            polarity: 'n',
            net: nNetName,
            sourceId: srcId,
            targetId: br.tgtNode.id,
            start: tapPoint,
            end: br.targetPoint,
            pathD: branchPath,
            isBranch: true,
          })

          junctionDots.push({
            id: `junc_n_${srcId}_${br.tgtNode.id}_${sIdx}`,
            polarity: 'n',
            x: tapX,
            y: nOrigin.y,
          })
        }

        // N 軌主幹繪製 (單一路徑直達主目標)
        const maxBranchTapX = nBranchTapXs.length > 0
          ? Math.max(...nBranchTapXs)
          : minTurnX
        const trunkTurnX = Math.min(
          primaryLeft - 10,
          Math.max(maxBranchTapX + 10, (maxBranchTapX + primaryLeft) / 2)
        )

        const isStraight = Math.abs(nPrimary.targetPoint.y - nOrigin.y) < 1.5
        const pathD = isStraight
          ? `M ${nOrigin.x} ${nOrigin.y} L ${nPrimary.targetPoint.x} ${nPrimary.targetPoint.y}`
          : generateOrthogonalPath(nOrigin, nPrimary.targetPoint, 4, trunkTurnX)

        edges.push({
          id: `edge_n_${srcId}_${nPrimary.tgtNode.id}_${sIdx}`,
          polarity: 'n',
          net: nNetName,
          sourceId: srcId,
          targetId: nPrimary.tgtNode.id,
          start: nOrigin,
          end: nPrimary.targetPoint,
          pathD,
          isBranch: false,
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
