/**
 * 库存查询相关纯函数（选做任务B：前端筛选逻辑单元测试）
 *
 * - isLowStock：低库存判定（库存 < 阈值 → 红色高亮）
 * - buildInventoryQuery：把筛选/分页条件构造成请求参数（空值剔除）
 */

// 库存低于该值判定为低库存（红色高亮）
export const LOW_STOCK_THRESHOLD = 10

/** 低库存判定：库存数量小于阈值返回 true（红色高亮） */
export function isLowStock(quantity: number, threshold: number = LOW_STOCK_THRESHOLD): boolean {
  return quantity < threshold
}

/**
 * 库存查询请求参数构造：
 * keyword（商品名/SKU 模糊）、warehouseId（仓库筛选）、page/pageSize（分页）。
 * 空筛选条件不携带，避免向后端发送无效参数。
 */
export function buildInventoryQuery(params: {
  keyword?: string
  warehouseId?: number
  page?: number
  pageSize?: number
}): Record<string, string | number> {
  const query: Record<string, string | number> = {
    page: params.page ?? 1,
    pageSize: params.pageSize ?? 20,
  }
  const keyword = params.keyword?.trim()
  if (keyword) query.keyword = keyword
  if (params.warehouseId !== undefined) query.warehouseId = params.warehouseId
  return query
}
