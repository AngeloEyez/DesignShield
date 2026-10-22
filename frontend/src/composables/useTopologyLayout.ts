/**
 * @file useTopologyLayout.ts
 * @description 通用電路拓撲排版狀態管理 Composable (雙引擎漸進式 POC 核心)
 * 1. 支援 'universal' (預設手刻純同步引擎) 與 'elk' (ELKjs 動態按需非同步引擎) 自由切換
 * 2. 封裝計算快取 (Layout Cache)、Loading 載入過渡狀態與錯誤防禦處理
 * 3. 確保 SVG 展示組件維持純渲染職責，遵守關注點分離架構
 */

import { ref, watch, shallowRef, type Ref } from 'vue'
import {
  computeUniversalTopologyLayout,
  type UniversalTopologyLayout,
} from '@/utils/universalTopologyLayout'
import { computeElkTopologyLayout } from '@/utils/elkTopologyLayout'

export type TopologyEngineType = 'universal' | 'elk'

export interface UseTopologyLayoutOptions {
  initialEngine?: TopologyEngineType
}

/**
 * 通用電路拓撲排版響應式 Composable
 *
 * @param {Ref<Record<string, any> | undefined>} evidenceRef - 傳入之 evidence trail 響應式參照
 * @param {UseTopologyLayoutOptions} options - 配置選項 (可指定初始引擎)
 * @returns 響應式排版狀態與操作介面
 */
export function useTopologyLayout(
  evidenceRef: Ref<Record<string, any> | undefined>,
  options: UseTopologyLayoutOptions = {}
) {
  const currentEngine = ref<TopologyEngineType>(options.initialEngine || 'universal')
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)

  // 預設純同步回退排版結構
  const emptyLayout: UniversalTopologyLayout = {
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

  const layout = shallowRef<UniversalTopologyLayout>(emptyLayout)

  // 雙引擎結果記憶快取 (以 engine#evidenceJson 為 Key)
  const layoutCache = new Map<string, UniversalTopologyLayout>()

  const computeLayout = async () => {
    const ev = evidenceRef.value
    if (!ev) {
      layout.value = emptyLayout
      isLoading.value = false
      return
    }

    const engine = currentEngine.value
    const cacheKey = `${engine}#${JSON.stringify(ev.topology || ev)}`

    if (layoutCache.has(cacheKey)) {
      layout.value = layoutCache.get(cacheKey)!
      isLoading.value = false
      return
    }

    error.value = null

    if (engine === 'universal') {
      try {
        const result = computeUniversalTopologyLayout(ev)
        layoutCache.set(cacheKey, result)
        layout.value = result
      } catch (err: any) {
        error.value = err?.message || 'Universal layout computation failed'
        layout.value = emptyLayout
      } finally {
        isLoading.value = false
      }
    } else {
      // ELKjs 動態非同步引擎
      isLoading.value = true
      try {
        const result = await computeElkTopologyLayout(ev)
        layoutCache.set(cacheKey, result)
        layout.value = result
      } catch (err: any) {
        error.value = err?.message || 'ELK layout computation failed'
        layout.value = emptyLayout
      } finally {
        isLoading.value = false
      }
    }
  }

  // 監聽資料與引擎變更自動重新排版
  watch([evidenceRef, currentEngine], () => {
    computeLayout()
  }, { immediate: true })

  /**
   * 切換排版引擎 (可在 'universal' 與 'elk' 間平滑切換)
   *
   * @param {TopologyEngineType} engine - 目標排版引擎
   */
  const setEngine = (engine: TopologyEngineType) => {
    if (currentEngine.value !== engine) {
      currentEngine.value = engine
    }
  }

  return {
    currentEngine,
    setEngine,
    layout,
    isLoading,
    error,
  }
}
