/**
 * @file ContainerSmoke.test.ts
 * @description 容器環境冒煙整合測試 (Container Smoke Test)
 * 確保運行中的 Docker 容器 (designshield-frontend-dev) 之 node_modules 與宿主機 package.json 100% 同步，
 * 並驗證 Vite Dev Server 能正確編譯與轉譯關鍵拓撲模組，杜絕套件脫節遺失問題。
 */

import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'
import { execSync } from 'child_process'
import http from 'http'

const FRONTEND_CONTAINER = 'designshield-frontend-dev'
const FRONTEND_PORT = process.env.FRONTEND_PORT || '8080'

function isContainerRunning(containerName: string): boolean {
  try {
    const stdout = execSync(
      `docker inspect --format '{{.State.Status}}' ${containerName}`,
      { stdio: ['pipe', 'pipe', 'ignore'], timeout: 3000 }
    ).toString()
    return stdout.trim() === 'running'
  } catch {
    return false
  }
}

function checkHttpModule(urlPath: string): Promise<{ statusCode?: number; body: string }> {
  return new Promise((resolve, reject) => {
    const req = http.get(`http://localhost:${FRONTEND_PORT}${urlPath}`, { timeout: 4000 }, (res) => {
      let data = ''
      res.on('data', (chunk) => {
        data += chunk
      })
      res.on('end', () => {
        resolve({ statusCode: res.statusCode, body: data })
      })
    })
    req.on('error', (err) => reject(err))
    req.on('timeout', () => {
      req.destroy()
      reject(new Error(`Request to ${urlPath} timed out`))
    })
  })
}

describe('容器環境冒煙測試 (Container Smoke Test)', () => {
  const containerRunning = isContainerRunning(FRONTEND_CONTAINER)

  it('若前端 Docker 容器在線，容器內 node_modules 必須與 package.json 依賴 100% 同步', () => {
    if (!containerRunning) {
      console.warn(`[ContainerSmoke] ${FRONTEND_CONTAINER} 未運行，跳過容器依賴同步檢查。`)
      expect(true).toBe(true)
      return
    }

    const pkgPath = path.resolve(__dirname, '../package.json')
    const pkgContent = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'))
    const dependencies = Object.keys(pkgContent.dependencies || {})

    const missingInContainer: string[] = []

    for (const pkg of dependencies) {
      try {
        execSync(`docker exec ${FRONTEND_CONTAINER} test -e /app/node_modules/${pkg}`, {
          stdio: ['pipe', 'pipe', 'ignore'],
          timeout: 2000,
        })
      } catch {
        missingInContainer.push(pkg)
      }
    }

    const failureMessage = missingInContainer.length > 0
      ? `\n🚨 容器內缺少依賴套件！\n` +
        `缺少清單: ${missingInContainer.join(', ')}\n` +
        `請執行修復指令:\n  docker exec ${FRONTEND_CONTAINER} npm install\n`
      : ''

    expect(missingInContainer, failureMessage).toEqual([])
  })

  it('若前端 Docker 容器在線，Vite Dev Server 必須能成功轉譯拓撲與核心組件', async () => {
    if (!containerRunning) {
      console.warn(`[ContainerSmoke] ${FRONTEND_CONTAINER} 未運行，跳過 Vite HTTP 轉譯檢查。`)
      expect(true).toBe(true)
      return
    }

    // 檢查拓撲排版演算法核心轉譯
    const resTopology = await checkHttpModule('/src/utils/universalTopologyLayout.ts')
    expect(resTopology.statusCode).toBe(200)
    expect(resTopology.body).not.toContain('Failed to resolve import')
    expect(resTopology.body).not.toContain('Internal server error')

    // 檢查 SVG 拓撲組件轉譯
    const resSvg = await checkHttpModule('/src/components/UniversalCircuitTopologySvg.vue')
    expect(resSvg.statusCode).toBe(200)
    expect(resSvg.body).not.toContain('Failed to resolve import')
    expect(resSvg.body).not.toContain('Internal server error')
  })
})
