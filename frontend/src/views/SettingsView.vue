<template>
  <div class="settings-page-container flex flex-col bg-surface-ground min-h-screen text-vscode-textMain pb-16">
    <!-- 頂部緊湊頁頭導航與動作列 (1px Grid Border) -->
    <div class="settings-header flex flex-wrap justify-between items-center gap-3 bg-surface-card px-4 py-2 border-b border-surface-border">
      <div class="header-left flex items-center gap-2.5">
        <Button
          v-tooltip.bottom="'返回 DRC 檢測主控台'"
          icon="pi pi-arrow-left"
          severity="secondary"
          size="small"
          outlined
          class="back-btn !w-7 !h-7 !p-0 shrink-0"
          @click="goBack"
        >
          <i class="pi pi-arrow-left text-xs"></i>
          <span class="sr-only">返回 DRC 檢測</span>
        </Button>
        <div class="header-titles flex items-center gap-2">
          <i class="pi pi-cog text-primary text-sm"></i>
          <h1 class="page-title text-sm font-semibold m-0 text-vscode-textHeading">
            系統環境與參數設定 (System Settings)
          </h1>
          <span class="hidden sm:inline-block text-[11px] font-mono px-1.5 py-0.2 rounded bg-surface-panel text-vscode-textMuted border border-surface-border">
            .env
          </span>
        </div>
      </div>

      <div class="header-actions flex items-center gap-1.5">
        <Button
          v-tooltip.bottom="'重設未儲存變更'"
          icon="pi pi-undo"
          severity="secondary"
          size="small"
          outlined
          class="!w-7 !h-7 !p-0"
          :disabled="!hasUnsavedChanges || isSaving"
          @click="resetChanges"
        >
          <i class="pi pi-undo text-xs"></i>
          <span class="sr-only">重設未儲存變更</span>
        </Button>
        <Button
          label="儲存設定"
          icon="pi pi-save"
          severity="primary"
          size="small"
          class="!py-1 !px-2.5 !text-xs"
          :loading="isSaving"
          :disabled="!hasUnsavedChanges"
          @click="saveSettings"
        />
        <Button
          v-tooltip.bottom="'重新啟動後端伺服器'"
          icon="pi pi-power-off"
          severity="danger"
          size="small"
          outlined
          class="!w-7 !h-7 !p-0"
          :loading="isRestarting"
          @click="confirmRestartServer"
        >
          <i class="pi pi-power-off text-xs"></i>
          <span class="sr-only">重啟服務器</span>
        </Button>
      </div>
    </div>

    <!-- 需重啟伺服器之警示提示橫幅 -->
    <div v-if="restartPromptVisible" class="alert-banner warning-banner flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 px-4 py-2 bg-amber-500/10 border-b border-amber-500/30 text-amber-600 dark:text-amber-400 text-xs">
      <div class="alert-content flex items-center gap-2">
        <i class="pi pi-exclamation-triangle alert-icon text-sm text-amber-500 shrink-0"></i>
        <div>
          <span class="alert-title font-semibold">系統提示：部分設定變更需要重新啟動伺服器才能完全生效</span>
          <span class="alert-desc text-vscode-textSecondary ml-2">
            受影響項目：<strong>{{ pendingRestartReasons.join(', ') }}</strong>
          </span>
        </div>
      </div>
      <Button
        label="立即重啟服務器"
        icon="pi pi-refresh"
        severity="warn"
        size="small"
        class="!py-1 !px-2.5 !text-xs shrink-0"
        :loading="isRestarting"
        @click="confirmRestartServer"
      />
    </div>

    <!-- 儲存成功通知橫幅 -->
    <div v-if="saveSuccessMessage" class="alert-banner success-banner flex items-center justify-between px-4 py-1.5 bg-emerald-500/10 border-b border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs">
      <div class="alert-content flex items-center gap-2">
        <i class="pi pi-check-circle alert-icon text-emerald-500"></i>
        <span>{{ saveSuccessMessage }}</span>
      </div>
      <button type="button" class="banner-close bg-transparent border-0 text-inherit cursor-pointer p-0.5" @click="saveSuccessMessage = ''">
        <i class="pi pi-times text-xs"></i>
      </button>
    </div>

    <!-- 磁碟儲存空間監控與垃圾清理 (40px 單行關鍵指標橫條 Compact Metric Strip) -->
    <div class="settings-card storage-card bg-surface-panel border-b border-surface-border flex flex-col">
      <div class="grid grid-cols-2 md:grid-cols-5 divide-x divide-surface-border items-center">
        <!-- 1. 上傳原始封裝 -->
        <div
          v-tooltip.bottom="`上傳原始封裝佔用：${formatBytes(storageStats.uploads.total_bytes)}`"
          class="metric-box px-3 py-2 flex items-center justify-between gap-2"
        >
          <span class="metric-label text-xs text-vscode-textMuted truncate">上傳封裝 (Uploads)</span>
          <div class="flex items-baseline gap-1.5 shrink-0 font-mono">
            <span class="metric-value text-xs font-semibold text-vscode-textHeading">{{ storageStats.uploads.file_count }} 檔</span>
            <span class="metric-sub text-[10px] text-vscode-textMuted">({{ formatBytes(storageStats.uploads.total_bytes) }})</span>
          </div>
        </div>

        <!-- 2. 解壓中繼暫存 -->
        <div
          v-tooltip.bottom="`解壓中繼暫存佔用：${formatBytes(storageStats.staging.total_bytes)}`"
          class="metric-box px-3 py-2 flex items-center justify-between gap-2"
        >
          <span class="metric-label text-xs text-vscode-textMuted truncate">解壓暫存 (Staging)</span>
          <div class="flex items-baseline gap-1.5 shrink-0 font-mono">
            <span class="metric-value text-xs font-semibold text-vscode-textHeading">{{ storageStats.staging.file_count }} 檔</span>
            <span class="metric-sub text-[10px] text-vscode-textMuted">({{ formatBytes(storageStats.staging.total_bytes) }})</span>
          </div>
        </div>

        <!-- 3. DRC 檢查報告 -->
        <div
          v-tooltip.bottom="`DRC 檢查報告佔用：${formatBytes(storageStats.reports.total_bytes)}`"
          class="metric-box px-3 py-2 flex items-center justify-between gap-2"
        >
          <span class="metric-label text-xs text-vscode-textMuted truncate">檢查報告 (Reports)</span>
          <div class="flex items-baseline gap-1.5 shrink-0 font-mono">
            <span class="metric-value text-xs font-semibold text-vscode-textHeading">{{ storageStats.reports.file_count }} 檔</span>
            <span class="metric-sub text-[10px] text-vscode-textMuted">({{ formatBytes(storageStats.reports.total_bytes) }})</span>
          </div>
        </div>

        <!-- 4. 總磁碟佔用 -->
        <div
          v-tooltip.bottom="`總計 ${storageStats.total_files} 個檔案`"
          class="metric-box highlight px-3 py-2 flex items-center justify-between gap-2 bg-primary-500/5"
        >
          <span class="metric-label text-xs text-vscode-textSecondary font-medium truncate">總磁碟佔用</span>
          <div class="flex items-baseline gap-1 shrink-0 font-mono">
            <span class="metric-value text-xs font-semibold text-primary">{{ storageStats.total_mb }} MB</span>
            <span class="metric-sub text-[10px] text-vscode-textMuted">({{ storageStats.total_files }} 檔)</span>
          </div>
        </div>

        <!-- 5. 空間重新整理與垃圾回收操作區 -->
        <div class="cleanup-actions px-3 py-1.5 flex items-center justify-between gap-2 col-span-2 md:col-span-1">
          <span class="text-[11px] text-vscode-textMuted truncate">空間維運</span>
          <div class="flex items-center gap-1.5">
            <Button
              v-tooltip.bottom="'重新整理磁碟空間指標'"
              icon="pi pi-refresh"
              severity="secondary"
              size="small"
              outlined
              class="!w-6 !h-6 !p-0 text-vscode-textSecondary hover:text-vscode-textHeading"
              :loading="isLoadingStats"
              @click="loadStorageStats"
            >
              <i class="pi pi-refresh text-xs"></i>
              <span class="sr-only">重新整理空間指標</span>
            </Button>
            <Button
              v-tooltip.bottom="'立即清理過期任務與孤兒檔案'"
              icon="pi pi-trash"
              severity="danger"
              size="small"
              outlined
              class="!w-6 !h-6 !p-0"
              :loading="isCleaning"
              @click="triggerCleanup"
            >
              <i class="pi pi-trash text-xs"></i>
              <span class="sr-only">立即清理過期任務與孤兒檔案</span>
            </Button>
          </div>
        </div>
      </div>

      <div v-if="cleanupMessage" class="cleanup-alert px-4 py-1.5 bg-emerald-500/10 border-t border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-1.5">
        <i class="pi pi-info-circle text-xs"></i>
        <span>{{ cleanupMessage }}</span>
      </div>
    </div>

    <!-- 設定分類切換標籤列 (1px Grid Border) -->
    <div class="category-tabs flex gap-1.5 overflow-x-auto px-4 py-2 bg-surface-card border-b border-surface-border">
      <button
        type="button"
        class="tab-btn px-2.5 py-1 text-xs font-medium rounded border cursor-pointer transition-colors whitespace-nowrap flex items-center gap-1.5"
        :class="selectedCategory === 'all' ? 'bg-primary-500 text-white border-primary-500' : 'bg-surface-panel border-surface-border text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
        @click="selectedCategory = 'all'"
      >
        <i class="pi pi-list text-[11px]"></i>
        <span>全部設定 ({{ envItems.length }})</span>
      </button>
      <button
        v-for="cat in categories"
        :key="cat.id"
        type="button"
        class="tab-btn px-2.5 py-1 text-xs font-medium rounded border cursor-pointer transition-colors whitespace-nowrap flex items-center gap-1.5"
        :class="selectedCategory === cat.id ? 'bg-primary-500 text-white border-primary-500' : 'bg-surface-panel border-surface-border text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
        @click="selectedCategory = cat.id"
      >
        <i :class="cat.icon" class="text-[11px]"></i>
        <span>{{ cat.name }} ({{ getCategoryItems(cat.id).length }})</span>
      </button>
    </div>

    <!-- 設定項目分組清單 (去容器化：1px divide-y 扁平雙行結構) -->
    <div class="settings-content-grid flex flex-col divide-y divide-surface-border">
      <div
        v-for="cat in displayCategories"
        :key="cat.id"
        class="category-group-card bg-surface-panel flex flex-col"
      >
        <!-- 分組標題列 -->
        <div class="group-header flex items-center gap-2 px-4 py-2 bg-surface-card border-b border-surface-border">
          <i :class="cat.icon" class="group-icon text-xs text-primary"></i>
          <h3 class="m-0 text-xs font-semibold text-vscode-textHeading">{{ cat.name }}</h3>
          <span class="env-source-tag text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-panel text-vscode-textMuted border border-surface-border ml-auto">
            .env
          </span>
        </div>

        <!-- LiteLLM 服務提供商快捷切換橫幅 -->
        <div v-if="cat.id === 'llm'" class="provider-switch-banner px-4 py-2 bg-surface-ground/60 border-b border-surface-border flex flex-wrap items-center justify-between gap-2">
          <span class="provider-switch-title text-xs font-medium text-vscode-textSecondary flex items-center gap-1.5 shrink-0">
            <i class="pi pi-sparkles text-primary text-xs"></i>
            <span>LiteLLM 服務提供者快捷切換：</span>
          </span>
          <div class="provider-chips-grid flex items-center gap-1.5 flex-wrap">
            <button
              v-for="p in supportedProviders"
              :key="p.id"
              type="button"
              v-tooltip.top="`${p.name} (${p.tag}) — ${p.keyHint}`"
              class="provider-badge-btn px-2.5 py-1 rounded border cursor-pointer flex items-center gap-1.5 text-xs transition-colors"
              :class="currentProvider === p.id ? 'bg-primary-500/15 border-primary text-primary font-semibold' : 'bg-surface-panel border-surface-border text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
              @click="selectProvider(p.id)"
            >
              <i :class="p.icon" class="text-[11px]"></i>
              <span class="provider-name">{{ p.name }}</span>
              <span class="provider-tag text-[10px] text-vscode-textMuted hidden sm:inline">({{ p.tag }})</span>
            </button>
          </div>
        </div>

        <!-- 設定項目 1px divide-y 緊湊 2 欄佈局 (左側控制與 key，右側說明文字) -->
        <div class="settings-items-list divide-y divide-surface-border">
          <div
            v-for="item in getCategoryItems(cat.id)"
            :key="item.key"
            class="setting-item-row px-4 py-3 grid grid-cols-1 lg:grid-cols-2 gap-4 items-start transition-colors hover:bg-surface-hover/30"
            :class="isItemChanged(item.key) ? 'bg-amber-500/5 border-l-2 border-l-amber-500' : ''"
          >
            <!-- 左側欄：第 1 行主說明 + 主 key + tag；第 2 行輸入元件 / toggle button -->
            <div class="setting-item-left flex flex-col gap-1.5 min-w-0">
              <!-- 第 1 行：主說明 (item.label) + 主 key (.env-key-badge) + 狀態 tag (需重啟/動態生效/已修改) -->
              <div class="meta-title-row flex items-center gap-1.5 flex-wrap">
                <span class="item-label font-semibold text-xs text-vscode-textHeading">{{ item.label }}</span>
                <code class="env-key-badge font-mono text-[11px] px-1.5 py-0.2 rounded bg-surface-card border border-surface-border text-primary font-medium">{{ item.key }}</code>
                <span
                  v-if="item.requires_restart"
                  class="badge-restart text-[10px] px-1.5 py-0.2 rounded bg-amber-500/15 border border-amber-500/30 text-amber-600 dark:text-amber-400 font-medium inline-flex items-center gap-1"
                >
                  <i class="pi pi-refresh text-[9px]"></i> 需重啟生效
                </span>
                <span
                  v-else
                  class="badge-dynamic text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 font-medium inline-flex items-center gap-1"
                >
                  <i class="pi pi-bolt text-[9px]"></i> 動態生效
                </span>
                <span
                  v-if="isItemChanged(item.key)"
                  class="badge-modified text-[10px] px-1.5 py-0.2 rounded bg-amber-500 text-white font-semibold"
                >
                  已修改
                </span>
              </div>

              <!-- 第 2 行：輸入控制元件 (InputText / Provider select / Model select / ToggleSwitch) -->
              <div class="setting-item-control w-full flex flex-col gap-1.5">
                <!-- LITELLM_PROVIDER 下拉切換選單 -->
                <div v-if="item.key === 'LITELLM_PROVIDER'" class="input-wrapper relative flex items-center w-full">
                  <select
                    v-model="formValues[item.key]"
                    class="setting-input provider-select w-full px-2.5 py-1 h-7 rounded border border-surface-border bg-surface-ground text-vscode-textHeading text-xs font-mono focus:outline-none focus:border-primary transition-colors cursor-pointer"
                    @change="selectProvider(formValues[item.key])"
                  >
                    <option v-for="p in supportedProviders" :key="p.id" :value="p.id" class="bg-surface-card text-vscode-textHeading">
                      {{ p.name }} ({{ p.tag }}) - provider: {{ p.id }}
                    </option>
                  </select>
                </div>

                <!-- LOCAL_LLM_MODEL 下拉與手動輸入組合 -->
                <div v-else-if="item.key === 'LOCAL_LLM_MODEL'" class="model-select-wrapper flex flex-col gap-1.5 w-full">
                  <div class="input-wrapper relative flex items-center w-full gap-1.5">
                    <InputText
                      v-model="formValues[item.key]"
                      type="text"
                      size="small"
                      class="setting-input model-input w-full !py-1 !px-2.5 text-xs font-mono bg-surface-ground border-surface-border text-vscode-textHeading"
                      list="llm-model-options"
                      :placeholder="item.default || item.example || '可直接輸入或自下拉選單選擇'"
                      @input="handleInput(item.key)"
                    />
                    <datalist id="llm-model-options">
                      <option v-for="m in availableLlmModels" :key="m" :value="m">{{ m }}</option>
                    </datalist>
                    <button
                      type="button"
                      v-tooltip.top="isFetchingModels ? '正在向伺服器查詢可用模型...' : '即時向伺服器查詢可用模型清單'"
                      class="btn-fetch-models px-2 py-1 h-7 text-xs rounded border border-surface-border bg-surface-card hover:bg-surface-hover text-vscode-textSecondary hover:text-vscode-textHeading cursor-pointer flex items-center gap-1 shrink-0 transition-colors"
                      :disabled="isFetchingModels"
                      @click="queryLlmModels(true)"
                    >
                      <i :class="isFetchingModels ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'" class="text-xs"></i>
                      <span class="sr-only">{{ isFetchingModels ? '查詢中...' : '重新整理' }}</span>
                    </button>
                  </div>

                  <!-- 下拉選單選擇器 -->
                  <div class="model-dropdown-row flex items-center gap-1.5 text-xs">
                    <label class="model-dropdown-label text-vscode-textMuted text-[11px] shrink-0" for="llm-model-select">
                      模型選單：
                    </label>
                    <select
                      id="llm-model-select"
                      class="model-select w-full px-2 py-0.5 h-6 rounded border border-surface-border bg-surface-ground text-vscode-textHeading text-xs font-mono focus:outline-none focus:border-primary transition-colors cursor-pointer"
                      :disabled="isFetchingModels"
                      @change="onModelSelectChange($event)"
                    >
                      <option value="" disabled :selected="!availableLlmModels.includes(formValues[item.key])" class="bg-surface-card text-vscode-textHeading">
                        {{ availableLlmModels.length > 0 ? `-- 點擊選擇模型 (共 ${availableLlmModels.length} 個) --` : '-- 尚無模型或點擊重新整理查詢 --' }}
                      </option>
                      <option
                        v-for="m in availableLlmModels"
                        :key="m"
                        :value="m"
                        :selected="formValues[item.key] === m"
                        class="bg-surface-card text-vscode-textHeading"
                      >
                        {{ m }}
                      </option>
                    </select>
                  </div>

                  <!-- 可用模型快速標籤 (Chips) -->
                  <div v-if="availableLlmModels.length > 0" class="model-chips-list flex flex-wrap items-center gap-1 text-xs">
                    <span
                      v-for="m in availableLlmModels"
                      :key="m"
                      class="model-chip px-1.5 py-0.2 rounded border text-[11px] cursor-pointer transition-colors font-mono"
                      :class="formValues[item.key] === m ? 'bg-primary-500/15 border-primary text-primary font-semibold' : 'border-surface-border bg-surface-card text-vscode-textSecondary hover:bg-surface-hover hover:text-vscode-textHeading'"
                      @click="applyModel(m)"
                    >
                      {{ m }}
                    </span>
                  </div>

                  <!-- 查詢狀態提示 -->
                  <div v-if="llmModelStatusMessage" class="model-status-hint text-[11px] flex items-center gap-1" :class="llmModelStatusSuccess ? 'text-emerald-500' : 'text-vscode-textMuted'">
                    <i :class="llmModelStatusSuccess ? 'pi pi-check-circle text-emerald-500' : 'pi pi-info-circle text-vscode-textMuted'" class="text-[10px]"></i>
                    <span>{{ llmModelStatusMessage }}</span>
                  </div>
                </div>

                <!-- 布林開關 (item_type === 'boolean') -->
                <div v-else-if="item.item_type === 'boolean'" class="boolean-switch-wrapper flex items-center justify-between px-2.5 py-1 rounded border border-surface-border bg-surface-ground w-full">
                  <div class="flex items-center gap-2">
                    <span
                      class="status-text text-[11px] font-medium px-1.5 py-0.2 rounded border flex items-center gap-1"
                      :class="isBooleanActive(item.key)
                        ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                        : 'bg-surface-card border-surface-border text-vscode-textMuted'"
                    >
                      <i :class="isBooleanActive(item.key) ? 'pi pi-check-circle text-emerald-500' : 'pi pi-ban text-vscode-textMuted'" class="text-[10px]"></i>
                      {{ isBooleanActive(item.key) ? '已啟用 (Enabled)' : '已停用 (Disabled)' }}
                    </span>
                    <span class="text-[11px] font-mono text-vscode-textMuted">
                      .env: <code class="text-primary font-semibold">{{ formValues[item.key] }}</code>
                    </span>
                  </div>
                  <ToggleSwitch
                    :model-value="isBooleanActive(item.key)"
                    class="setting-boolean-switch scale-75 origin-right"
                    @update:model-value="setBooleanValue(item.key, $event)"
                  />
                </div>

                <!-- 一般文字/密鑰輸入框 -->
                <div v-else class="input-wrapper relative flex items-center w-full">
                  <InputText
                    v-if="!item.is_secret || visibleSecrets[item.key]"
                    v-model="formValues[item.key]"
                    type="text"
                    size="small"
                    class="setting-input w-full !py-1 !px-2.5 text-xs font-mono bg-surface-ground border-surface-border text-vscode-textHeading"
                    :placeholder="item.default || item.example || '請輸入設定值'"
                    @input="handleInput(item.key)"
                    @blur="item.key === 'LOCAL_LLM_URL' ? queryLlmModels(false) : null"
                  />
                  <InputText
                    v-else
                    v-model="formValues[item.key]"
                    type="password"
                    size="small"
                    class="setting-input w-full !py-1 !px-2.5 !pr-7 text-xs font-mono bg-surface-ground border-surface-border text-vscode-textHeading"
                    :placeholder="item.default || item.example || '請輸入設定值'"
                    @input="handleInput(item.key)"
                  />
                  <button
                    v-if="item.is_secret"
                    type="button"
                    v-tooltip.left="visibleSecrets[item.key] ? '隱藏金鑰' : '顯示金鑰'"
                    class="btn-toggle-secret absolute right-2 text-vscode-textMuted hover:text-vscode-textHeading cursor-pointer bg-transparent border-0 text-xs"
                    @click="toggleSecret(item.key)"
                  >
                    <i :class="visibleSecrets[item.key] ? 'pi pi-eye-slash' : 'pi pi-eye'"></i>
                  </button>
                </div>

                <!-- 若有修改顯示原值 -->
                <div v-if="isItemChanged(item.key)" class="original-val-hint text-[10px] text-vscode-textMuted">
                  原設定值：<code class="bg-surface-card px-1 py-0.2 rounded text-amber-600 dark:text-amber-400 font-mono border border-surface-border">{{ originalValues[item.key] || '(空值)' }}</code>
                </div>
              </div>
            </div>

            <!-- 右側欄：佔用與左側相同高度，放說明文字與範例格式 -->
            <div
              v-tooltip.bottom="formatItemTooltip(item)"
              class="setting-item-doc flex flex-col justify-start gap-1.5 text-xs py-0.5 min-w-0"
            >
              <p class="item-description text-xs text-vscode-textMain m-0 leading-relaxed whitespace-pre-wrap">
                {{ item.description }}
              </p>
              <div
                v-if="item.example && !item.description?.includes(item.example)"
                class="item-example-box text-[11px] text-vscode-textMuted font-mono flex items-center gap-1.5 mt-0.5"
              >
                <span class="shrink-0">範例格式：</span>
                <code class="px-1.5 py-0.2 rounded bg-surface-ground border border-surface-border text-vscode-textSecondary break-all">{{ item.example }}</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部固定儲存浮動列 (當有未儲存變更時浮現) -->
    <div v-if="hasUnsavedChanges" class="floating-save-bar fixed bottom-4 left-1/2 -translate-x-1/2 z-50 bg-surface-panel border border-primary/60 rounded-lg px-4 py-2 shadow-xl flex items-center gap-4 text-xs text-vscode-textMain">
      <div class="save-bar-info flex items-center gap-1.5">
        <i class="pi pi-info-circle text-primary"></i>
        <span>您有 <strong class="text-vscode-textHeading">{{ changedKeysCount }}</strong> 個設定項目尚未儲存至 <code class="font-mono text-primary">.env</code></span>
      </div>
      <div class="save-bar-actions flex items-center gap-2">
        <Button label="放棄變更" severity="secondary" size="small" outlined class="!py-1 !px-2 !text-xs" @click="resetChanges" />
        <Button
          label="立即儲存設定"
          icon="pi pi-check"
          severity="primary"
          size="small"
          class="!py-1 !px-2.5 !text-xs"
          :loading="isSaving"
          @click="saveSettings"
        />
      </div>
    </div>

    <!-- 重啟確認對話框 -->
    <div v-if="showRestartConfirm" class="modal-backdrop fixed inset-0 bg-black/50 backdrop-blur-sm z-[999] flex items-center justify-center p-4" @click.self="showRestartConfirm = false">
      <div class="modal-dialog bg-surface-panel border border-surface-border rounded-md max-w-md w-full p-4 flex flex-col gap-3 shadow-xl text-vscode-textMain">
        <div class="dialog-header flex items-center gap-2 text-red-500 text-sm font-semibold">
          <i class="pi pi-power-off text-red-500"></i>
          <h3 class="m-0 text-sm font-semibold text-vscode-textHeading">確認重啟伺服器？</h3>
        </div>
        <div class="dialog-body flex flex-col gap-1.5 text-xs text-vscode-textSecondary">
          <p class="m-0 leading-relaxed">您即將發送指令重新啟動 DesignShield 後端伺服器服務。</p>
          <p class="text-vscode-textMuted text-xs m-0 leading-relaxed">
            重啟期間 API 連線將暫時中斷約 5~10 秒，頁面會自動監測連線狀況並在服務恢復時自動重新連線。
          </p>
        </div>
        <div class="dialog-footer flex justify-end gap-2 pt-2 border-t border-surface-border">
          <Button label="取消" severity="secondary" size="small" outlined @click="showRestartConfirm = false" />
          <Button
            label="確定重啟"
            icon="pi pi-check"
            severity="danger"
            size="small"
            :loading="isRestarting"
            @click="executeRestart"
          />
        </div>
      </div>
    </div>

    <!-- 重啟中連線輪詢等待覆蓋遮罩 -->
    <div v-if="isReconnecting" class="reconnect-overlay fixed inset-0 bg-black/60 backdrop-blur-md z-[1000] flex items-center justify-center p-4">
      <div class="reconnect-box bg-surface-panel border border-surface-border rounded-lg p-6 max-w-md w-full text-center flex flex-col items-center gap-2.5 shadow-xl">
        <div class="spinner-icon text-2xl text-primary animate-spin">
          <i class="pi pi-spin pi-spinner"></i>
        </div>
        <h3 class="m-0 text-sm font-semibold text-vscode-textHeading">伺服器正在重新啟動中...</h3>
        <p class="reconnect-desc text-xs text-vscode-textMuted m-0 leading-relaxed">
          已發送重啟訊號，正在偵測服務健康狀態 (已等待 {{ reconnectTimer }} 秒 / 最長等待 120 秒)...
        </p>
        <div class="ping-status text-xs text-vscode-textSecondary flex items-center gap-2 bg-surface-card px-3 py-1 rounded-full border border-surface-border">
          <i class="pi pi-circle-fill text-[8px] text-amber-500 animate-pulse"></i>
          <span>正在探測端點：<code class="text-primary font-mono">{{ healthCheckEndpointUrl }}</code></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file SettingsView.vue
 * @description 系統環境與參數設定頁面 (2026 緊湊雙行列表 + 40px 指標橫條雙主題版)
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import ToggleSwitch from 'primevue/toggleswitch'
import InputText from 'primevue/inputtext'
import {
  fetchEnvSettings,
  updateEnvSettings,
  restartServer,
  fetchStorageStats,
  triggerStorageCleanup,
  checkServerHealth,
  fetchAvailableLlmModels,
} from '@/services/api'
import type { EnvSettingItem, EnvCategory, StorageStats } from '@/types/settings'

const router = useRouter()

// 資料狀態
const envItems = ref<EnvSettingItem[]>([])
const categories = ref<EnvCategory[]>([])
const formValues = ref<Record<string, string>>({})
const originalValues = ref<Record<string, string>>({})
const visibleSecrets = ref<Record<string, boolean>>({})

// LLM 可用模型即時查詢狀態
const availableLlmModels = ref<string[]>([])
const isFetchingModels = ref<boolean>(false)
const llmModelStatusMessage = ref<string>('')
const llmModelStatusSuccess = ref<boolean>(true)

// 分類切換
const selectedCategory = ref<string>('all')

// 載入與動作狀態
const isLoading = ref<boolean>(false)
const isSaving = ref<boolean>(false)
const isRestarting = ref<boolean>(false)
const isReconnecting = ref<boolean>(false)
const reconnectTimer = ref<number>(0)
let reconnectInterval: any = null

const showRestartConfirm = ref<boolean>(false)
const saveSuccessMessage = ref<string>('')
const restartPromptVisible = ref<boolean>(false)
const pendingRestartReasons = ref<string[]>([])

// 磁碟空間狀態
const storageStats = ref<StorageStats>({
  total_files: 0,
  total_bytes: 0,
  total_mb: 0.0,
  uploads: { file_count: 0, total_bytes: 0 },
  staging: { file_count: 0, total_bytes: 0 },
  reports: { file_count: 0, total_bytes: 0 },
})
const isLoadingStats = ref<boolean>(false)
const isCleaning = ref<boolean>(false)
const cleanupMessage = ref<string>('')

/**
 * 組合設定項目完整說明與範例格式供 Tooltip 呈現
 */
const formatItemTooltip = (item: EnvSettingItem): string => {
  if (item.example) {
    return `${item.description}\n範例格式：${item.example}`
  }
  return item.description || item.label
}

// 計算屬性：是否有尚未儲存的變更
const hasUnsavedChanges = computed(() => {
  for (const k of Object.keys(formValues.value)) {
    if (formValues.value[k] !== originalValues.value[k]) {
      return true
    }
  }
  return false
})

const changedKeysCount = computed(() => {
  let count = 0
  for (const k of Object.keys(formValues.value)) {
    if (formValues.value[k] !== originalValues.value[k]) {
      count++
    }
  }
  return count
})

const isItemChanged = (key: string): boolean => {
  return formValues.value[key] !== originalValues.value[key]
}

const displayCategories = computed(() => {
  if (selectedCategory.value === 'all') {
    return categories.value
  }
  return categories.value.filter((c) => c.id === selectedCategory.value)
})

/**
 * 動態計算健康探測端點網址 (Health Check URL)
 */
const healthCheckEndpointUrl = computed(() => {
  const host = formValues.value['SERVER_HOST'] || (typeof window !== 'undefined' ? window.location.hostname : '192.168.1.16')
  const port = formValues.value['FRONTEND_PORT'] || (typeof window !== 'undefined' && window.location.port ? window.location.port : '8080')
  const protocol = typeof window !== 'undefined' && window.location.protocol ? window.location.protocol : 'http:'
  return `${protocol}//${host}:${port}/api/v1/health`
})

const getCategoryItems = (catId: string): EnvSettingItem[] => {
  return envItems.value.filter((item) => item.category === catId)
}

const toggleSecret = (key: string) => {
  visibleSecrets.value[key] = !visibleSecrets.value[key]
}

const handleInput = (_key: string) => {
  // 自動追蹤變更
}

const isBooleanActive = (key: string): boolean => {
  const val = String(formValues.value[key] ?? '').toLowerCase().trim()
  return val === 'true' || val === '1' || val === 'yes'
}

const setBooleanValue = (key: string, enabled: boolean) => {
  formValues.value[key] = enabled ? 'true' : 'false'
  handleInput(key)
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 支援之 LiteLLM 服務提供者定義
interface LlmProviderOption {
  id: string
  name: string
  tag: string
  icon: string
  defaultUrl: string
  defaultModel: string
  keyHint: string
}

const supportedProviders: LlmProviderOption[] = [
  {
    id: 'local',
    name: '本地推理',
    tag: 'vLLM / Ollama',
    icon: 'pi pi-server',
    defaultUrl: 'http://192.168.1.5:8000/v1',
    defaultModel: 'openai/qwen',
    keyHint: '本地端點未啟用鑑權填 EMPTY 即可'
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    tag: 'AI Studio',
    icon: 'pi pi-bolt',
    defaultUrl: 'https://generativelanguage.googleapis.com',
    defaultModel: 'gemini/gemini-2.5-flash',
    keyHint: '請填入 Google AI Studio API Key (AIzaSy...)'
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    tag: '聚合網關',
    icon: 'pi pi-globe',
    defaultUrl: 'https://openrouter.ai/api/v1',
    defaultModel: 'openrouter/google/gemini-2.5-flash',
    keyHint: '請填入 OpenRouter API Key (sk-or-v1-...)'
  },
  {
    id: 'openai',
    name: 'OpenAI 官方',
    tag: 'GPT-4o',
    icon: 'pi pi-microchip',
    defaultUrl: 'https://api.openai.com/v1',
    defaultModel: 'openai/gpt-4o',
    keyHint: '請填入 OpenAI API Key (sk-proj-...)'
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    tag: 'Claude 3.5',
    icon: 'pi pi-comments',
    defaultUrl: 'https://api.anthropic.com',
    defaultModel: 'anthropic/claude-3-5-sonnet-20241022',
    keyHint: '請填入 Anthropic API Key (sk-ant-...)'
  },
  {
    id: 'groq',
    name: 'Groq',
    tag: '極速推理',
    icon: 'pi pi-forward',
    defaultUrl: 'https://api.groq.com/openai/v1',
    defaultModel: 'groq/llama-3.3-70b-versatile',
    keyHint: '請填入 Groq API Key (gsk_...)'
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    tag: '官方 API',
    icon: 'pi pi-search',
    defaultUrl: 'https://api.deepseek.com/v1',
    defaultModel: 'deepseek/deepseek-chat',
    keyHint: '請填入 DeepSeek API Key (sk-...)'
  },
]

const currentProvider = computed(() => {
  if (formValues.value['LITELLM_PROVIDER']) {
    return formValues.value['LITELLM_PROVIDER'].toLowerCase()
  }
  const model = (formValues.value['LOCAL_LLM_MODEL'] || '').toLowerCase()
  if (model.startsWith('gemini/')) return 'gemini'
  if (model.startsWith('openrouter/')) return 'openrouter'
  if (model.startsWith('anthropic/') || model.startsWith('claude')) return 'anthropic'
  if (model.startsWith('groq/')) return 'groq'
  if (model.startsWith('deepseek/')) return 'deepseek'
  return 'local'
})

const selectProvider = (providerId: string) => {
  if (!providerId) return
  formValues.value['LITELLM_PROVIDER'] = providerId
  handleInput('LITELLM_PROVIDER')

  const providerDef = supportedProviders.find((p) => p.id === providerId)
  if (providerDef) {
    const curUrl = formValues.value['LOCAL_LLM_URL'] || ''
    const isOtherDefault = supportedProviders.some((p) => p.defaultUrl === curUrl)
    if (!curUrl || isOtherDefault || (providerId === 'gemini' && curUrl.includes('192.168.1.5'))) {
      formValues.value['LOCAL_LLM_URL'] = providerDef.defaultUrl
      handleInput('LOCAL_LLM_URL')
    }

    const curModel = (formValues.value['LOCAL_LLM_MODEL'] || '').trim()
    const isOtherProviderModel =
      (providerId === 'local' && (curModel.startsWith('gemini/') || curModel.startsWith('openrouter/') || curModel.startsWith('groq/') || curModel.startsWith('deepseek/') || curModel.startsWith('anthropic/'))) ||
      (providerId === 'gemini' && !curModel.startsWith('gemini/')) ||
      (providerId === 'openrouter' && !curModel.startsWith('openrouter/')) ||
      (providerId === 'groq' && !curModel.startsWith('groq/')) ||
      (providerId === 'deepseek' && !curModel.startsWith('deepseek/')) ||
      (providerId === 'anthropic' && !curModel.startsWith('anthropic/'))

    if (!curModel || isOtherProviderModel) {
      formValues.value['LOCAL_LLM_MODEL'] = providerDef.defaultModel
      handleInput('LOCAL_LLM_MODEL')
    }

    queryLlmModels(true, providerId)
  }
}

// 載入 .env 設定資料
const loadEnvSettings = async () => {
  isLoading.value = true
  try {
    const data = await fetchEnvSettings()
    envItems.value = data.items
    categories.value = data.categories

    const forms: Record<string, string> = {}
    const origs: Record<string, string> = {}
    for (const item of data.items) {
      forms[item.key] = item.value !== null && item.value !== undefined ? String(item.value) : ''
      origs[item.key] = forms[item.key]
    }
    formValues.value = forms
    originalValues.value = origs

    queryLlmModels(false)
  } catch (err) {
    console.error('Failed to load env settings:', err)
  } finally {
    isLoading.value = false
  }
}

// 即時向 LiteLLM 伺服器端點或 Provider 查詢可用模型
const queryLlmModels = async (manual = false, forceProvider?: string) => {
  const p = forceProvider || currentProvider.value
  const url = formValues.value['LOCAL_LLM_URL'] || ''
  let key = formValues.value['LOCAL_LLM_API_KEY'] || ''
  if (p === 'gemini' && formValues.value['GEMINI_API_KEY']) {
    key = formValues.value['GEMINI_API_KEY']
  } else if (p === 'openrouter' && formValues.value['OPENROUTER_API_KEY']) {
    key = formValues.value['OPENROUTER_API_KEY']
  }

  isFetchingModels.value = true
  if (manual) {
    const provName = supportedProviders.find((sp) => sp.id === p)?.name || p
    llmModelStatusMessage.value = `正在查詢 ${provName} 可用模型清單...`
  }

  try {
    const res = await fetchAvailableLlmModels(p, url, key)
    if (res && res.success && Array.isArray(res.models) && res.models.length > 0) {
      availableLlmModels.value = res.models
      llmModelStatusSuccess.value = true
      llmModelStatusMessage.value = res.message || `成功取得 ${res.models.length} 個可用模型`
    } else {
      llmModelStatusSuccess.value = false
      llmModelStatusMessage.value = res?.message || '未能取得模型清單，支援手動輸入模型名稱'
    }
  } catch (err: any) {
    llmModelStatusSuccess.value = false
    llmModelStatusMessage.value = '連線至模型伺服器端點失敗，支援手動輸入模型名稱'
  } finally {
    isFetchingModels.value = false
  }
}

const onModelSelectChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  if (target && target.value) {
    formValues.value['LOCAL_LLM_MODEL'] = target.value
    handleInput('LOCAL_LLM_MODEL')
  }
}

const applyModel = (modelName: string) => {
  formValues.value['LOCAL_LLM_MODEL'] = modelName
  handleInput('LOCAL_LLM_MODEL')
}

// 載入磁碟空間指標
const loadStorageStats = async () => {
  isLoadingStats.value = true
  try {
    const data = await fetchStorageStats()
    if (data) {
      storageStats.value = data
    }
  } catch (err) {
    console.error('Failed to load storage stats:', err)
  } finally {
    isLoadingStats.value = false
  }
}

// 觸發磁碟空間清理
const triggerCleanup = async () => {
  isCleaning.value = true
  cleanupMessage.value = ''
  try {
    const res = await triggerStorageCleanup()
    if (res) {
      const tasksCount = res.expired_tasks_count ?? 0
      const orphanCount = res.orphan_files_count ?? 0
      cleanupMessage.value = `清理成功！已釋放 ${res.freed_mb} MB 空間，清除 ${tasksCount} 個過期任務與 ${orphanCount} 個孤兒檔案。`
      await loadStorageStats()
    }
  } catch (err) {
    cleanupMessage.value = '清理失敗，請檢閱後端日誌。'
    console.error('Cleanup error:', err)
  } finally {
    isCleaning.value = false
  }
}

// 放棄變更並還原
const resetChanges = () => {
  formValues.value = { ...originalValues.value }
}

// 儲存設定至 .env
const saveSettings = async () => {
  isSaving.value = true
  saveSuccessMessage.value = ''

  try {
    const payload: Record<string, any> = {}
    for (const k of Object.keys(formValues.value)) {
      if (formValues.value[k] !== originalValues.value[k]) {
        payload[k] = formValues.value[k]
      }
    }

    if (Object.keys(payload).length === 0) {
      isSaving.value = false
      return
    }

    const res = await updateEnvSettings(payload)
    if (res.success) {
      originalValues.value = { ...formValues.value }
      saveSuccessMessage.value = res.message || '設定已成功儲存至 .env 檔案！'

      if (res.requires_restart) {
        restartPromptVisible.value = true
        pendingRestartReasons.value = res.restart_reasons || []
      } else {
        restartPromptVisible.value = false
      }
    }
  } catch (err) {
    console.error('Failed to save settings:', err)
  } finally {
    isSaving.value = false
  }
}

// 重啟伺服器確認與執行
const confirmRestartServer = () => {
  showRestartConfirm.value = true
}

const executeRestart = async () => {
  showRestartConfirm.value = false
  isRestarting.value = true
  isReconnecting.value = true
  reconnectTimer.value = 0

  try {
    await restartServer()
  } catch (err) {
    console.error('Trigger restart error (expected during process restart):', err)
  }

  let checkInFlight = false
  reconnectInterval = setInterval(async () => {
    reconnectTimer.value += 1

    if (reconnectTimer.value >= 3 && !checkInFlight) {
      checkInFlight = true
      try {
        const isAlive = await checkServerHealth()
        if (isAlive) {
          clearInterval(reconnectInterval)
          reconnectInterval = null
          isReconnecting.value = false
          isRestarting.value = false
          restartPromptVisible.value = false
          saveSuccessMessage.value = '✅ 伺服器已成功重啟完成並恢復連線！'
          await loadEnvSettings()
          await loadStorageStats()
          return
        }
      } catch {
        // 重啟過程中網路暫時中斷屬預期狀況，持續探測
      } finally {
        checkInFlight = false
      }
    }

    if (reconnectTimer.value >= 120) {
      if (reconnectInterval) {
        clearInterval(reconnectInterval)
        reconnectInterval = null
      }
      isReconnecting.value = false
      isRestarting.value = false
      alert('伺服器重啟探測逾時 (已等待 120 秒)，請手動刷新頁面或確認容器執行狀態。')
    }
  }, 1000)
}

const goBack = () => {
  router.push('/')
}

onMounted(() => {
  loadEnvSettings()
  loadStorageStats()
})

onUnmounted(() => {
  if (reconnectInterval) {
    clearInterval(reconnectInterval)
  }
})
</script>
