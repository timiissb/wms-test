import api from './client'

// ============ 商品（参考实现） ============

export interface Product {
  id: number
  name: string
  sku: string
  unit: string
  createdAt: string
  updatedAt: string
}

export const getProducts = (keyword?: string) =>
  api.get<any, { code: number; data: Product[] }>('/products', { params: { keyword } })

export const createProduct = (data: { name: string; sku: string; unit?: string }) =>
  api.post('/products', data)

export const updateProduct = (id: number, data: { name: string; unit?: string }) =>
  api.put(`/products/${id}`, data)

export const deleteProduct = (id: number) =>
  api.delete(`/products/${id}`)


// ============ 仓库 & 库位 ============

export interface Warehouse {
  id: number
  code: string
  name: string
}

export interface Location {
  id: number
  warehouseId: number
  code: string
  status: string
}

export const getWarehouses = () =>
  api.get<any, { code: number; data: Warehouse[] }>('/warehouses')

export const getLocations = (warehouseId: number) =>
  api.get<any, { code: number; data: Location[] }>(`/warehouses/${warehouseId}/locations`)


// ============ 库存查询（候选人实现） ============

export interface InventoryItem {
  productId: number
  productName: string
  sku: string
  locationCode: string
  warehouseName: string
  quantity: number
  updatedAt: string
}

export const getInventory = (params: {
  keyword?: string
  warehouseId?: number
  page?: number
  pageSize?: number
}) =>
  api.get<any, { code: number; data: { list: InventoryItem[]; total: number; page: number; pageSize: number } }>(
    '/inventory',
    { params }
  )


// ============ 入库单（候选人实现） ============

// 字段与接口文档一致（camelCase），后端 Pydantic 已通过 alias 接收/返回 camelCase

export interface InboundItemRequest {
  productId: number
  quantity: number
  locationCode: string
}

export interface InboundOrderItemResponse {
  productId: number
  productName: string | null
  quantity: number
  locationCode: string
}

export interface InboundOrder {
  id: number
  orderNo: string
  supplierName: string
  status: string
  items: InboundOrderItemResponse[]
  createdAt: string
}

export const createInboundOrder = (data: {
  supplierName: string
  items: InboundItemRequest[]
}) =>
  api.post<any, { code: number; message: string; data: InboundOrder }>(
    '/inbound-orders',
    data
  )


// ============ 出库单（选做任务A） ============

export interface OutboundItemRequest {
  productId: number
  quantity: number
  locationCode: string
}

export interface OutboundOrderItemResponse {
  productId: number
  productName: string | null
  quantity: number
  locationCode: string
}

export interface OutboundOrder {
  id: number
  orderNo: string
  customerName: string
  status: string
  items: OutboundOrderItemResponse[]
  createdAt: string
}

export const createOutboundOrder = (data: {
  customerName: string
  items: OutboundItemRequest[]
}) =>
  api.post<any, { code: number; message: string; data: OutboundOrder }>(
    '/outbound-orders',
    data
  )
