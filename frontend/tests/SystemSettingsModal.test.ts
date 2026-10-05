import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SystemSettingsModal from '../src/components/SystemSettingsModal.vue'
import Button from 'primevue/button'
import axios from 'axios'

vi.mock('axios')

describe('SystemSettingsModal.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(axios.get as any).mockImplementation((url: string) => {
      if (url === '/api/v1/settings/storage-stats') {
        return Promise.resolve({
          data: {
            total_files: 10,
            total_bytes: 1048576,
            total_mb: 1.0,
            uploads: { file_count: 4, total_bytes: 524288 },
            staging: { file_count: 5, total_bytes: 524288 },
            reports: { file_count: 1, total_bytes: 0 }
          }
        })
      }
      if (url === '/api/v1/settings') {
        return Promise.resolve({
          data: [
            { key: 'upload_retention_days', value: { days: 14 } },
            { key: 'task_timeout_seconds', value: { seconds: 1800 } },
            { key: 'llm_config', value: { api_base: 'http://test-llm:8000/v1', model: 'mock-llm' } }
          ]
        })
      }
      return Promise.resolve({ data: {} })
    })
    ;(axios.post as any).mockResolvedValue({
      data: {
        retention_days: 14,
        freed_mb: 0.5,
        deleted_files_count: 3
      }
    })
    ;(axios.put as any).mockResolvedValue({ data: { success: true } })
  })

  it('renders modal when visible is true', async () => {
    const wrapper = mount(SystemSettingsModal, {
      props: { visible: true },
      global: {
        components: { Button }
      }
    })

    expect(wrapper.text()).toContain('系統運維與參數設定')
    expect(wrapper.text()).toContain('磁碟儲存空間監控與垃圾回收')
    expect(wrapper.text()).toContain('暫存檔案保留天數')
  })

  it('emits update:visible false when close button is clicked', async () => {
    const wrapper = mount(SystemSettingsModal, {
      props: { visible: true },
      global: {
        components: { Button }
      }
    })

    const closeBtn = wrapper.find('.close-btn')
    await closeBtn.trigger('click')

    expect(wrapper.emitted('update:visible')).toBeTruthy()
    expect(wrapper.emitted('update:visible')![0]).toEqual([false])
  })

  it('triggers cleanup and displays result message', async () => {
    const wrapper = mount(SystemSettingsModal, {
      props: { visible: true },
      global: {
        components: { Button }
      }
    })

    // 找到立即清理按鈕
    const buttons = wrapper.findAllComponents(Button)
    const cleanupBtn = buttons.find(b => b.text().includes('立即清理過期暫存'))
    expect(cleanupBtn).toBeDefined()

    await cleanupBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))

    expect(axios.post).toHaveBeenCalled()
    expect(wrapper.text()).toContain('清理完成！共釋放 0.5 MB 磁碟空間')
  })

  it('saves settings when save button is clicked', async () => {
    const wrapper = mount(SystemSettingsModal, {
      props: { visible: true },
      global: {
        components: { Button }
      }
    })

    const buttons = wrapper.findAllComponents(Button)
    const saveBtn = buttons.find(b => b.text().includes('儲存設定'))
    expect(saveBtn).toBeDefined()

    await saveBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 50))

    expect(axios.put).toHaveBeenCalledWith(
      '/api/v1/settings/upload_retention_days',
      expect.objectContaining({ value: { days: 7 } })
    )
  })
})
