/**
 * 库存列表筛选逻辑单元测试（选做任务B）
 *
 * 覆盖：
 * 1. keyword 模糊筛选（商品名/SKU）
 * 2. 仓库筛选（warehouseId）
 * 3. 低库存高亮判定（quantity < 10）
 */
import { describe, it, expect } from 'vitest'
import { isLowStock, buildInventoryQuery } from './inventory'

describe('低库存高亮判定 isLowStock', () => {
  it('库存低于阈值（10）时标记高亮', () => {
    expect(isLowStock(0)).toBe(true)
    expect(isLowStock(9)).toBe(true)
  })

  it('库存达到阈值（10）及以上不标记高亮', () => {
    expect(isLowStock(10)).toBe(false)
    expect(isLowStock(100)).toBe(false)
  })

  it('支持自定义阈值', () => {
    expect(isLowStock(15, 20)).toBe(true)
    expect(isLowStock(15, 10)).toBe(false)
  })
})

describe('库存查询参数构造 buildInventoryQuery', () => {
  it('keyword 筛选：非空关键字携带到请求参数', () => {
    expect(buildInventoryQuery({ keyword: '蓝牙', page: 1, pageSize: 20 })).toEqual({
      page: 1,
      pageSize: 20,
      keyword: '蓝牙',
    })
  })

  it('keyword 为空白时不出现在请求参数中', () => {
    const q = buildInventoryQuery({ keyword: '  ', page: 1, pageSize: 20 })
    expect(q).not.toHaveProperty('keyword')
  })

  it('仓库筛选：warehouseId 携带到请求参数', () => {
    expect(buildInventoryQuery({ warehouseId: 2, page: 1, pageSize: 20 })).toMatchObject({
      warehouseId: 2,
      page: 1,
      pageSize: 20,
    })
  })

  it('未选仓库时不含 warehouseId 参数', () => {
    const q = buildInventoryQuery({ page: 1, pageSize: 20 })
    expect(q).not.toHaveProperty('warehouseId')
  })

  it('分页默认值：page=1、pageSize=20', () => {
    expect(buildInventoryQuery({})).toEqual({ page: 1, pageSize: 20 })
  })
})
