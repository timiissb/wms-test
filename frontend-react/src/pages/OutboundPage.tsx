/**
 * ============================================
 *  出库管理页 — 选做任务A 实现
 * ============================================
 *
 * 需求：
 * 1. 表单：客户名称 + 出库明细列表
 * 2. 明细行：商品下拉搜索 → 仓库 → 库位级联 → 数量
 * 3. 提交（调用 POST /api/outbound-orders，字段 camelCase）
 *    - 库存不足时后端返回 400，前端展示错误信息
 *
 * 参考 InboundPage.tsx 的实现风格
 */
import { useState, useEffect } from 'react'
import { Input, Button, Select, InputNumber, message } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import {
  createOutboundOrder,
  getProducts,
  getWarehouses,
  getLocations,
  type Product,
  type Warehouse,
  type Location,
} from '@/api'

interface OutboundItem {
  productId?: number
  warehouseId?: number
  locationCode?: string
  quantity: number
}

const productOptions = (products: Product[]) =>
  products.map((p) => ({ label: `${p.name}（${p.sku}）`, value: p.id }))

export default function OutboundPage() {
  const [customerName, setCustomerName] = useState('')
  const [items, setItems] = useState<OutboundItem[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const [locationsMap, setLocationsMap] = useState<Record<number, Location[]>>({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadProducts()
    loadWarehouses()
  }, [])

  const loadProducts = async () => {
    try {
      const res = await getProducts()
      setProducts(res.data)
    } catch (e: any) {
      message.error('加载商品失败: ' + (e.response?.data?.message || e.message))
    }
  }

  const loadWarehouses = async () => {
    try {
      const res = await getWarehouses()
      setWarehouses(res.data)
    } catch (e: any) {
      message.error('加载仓库失败: ' + (e.response?.data?.message || e.message))
    }
  }

  const loadLocations = async (warehouseId: number) => {
    // 已加载过的仓库库位直接复用缓存，避免重复请求
    if (locationsMap[warehouseId]) return
    try {
      const res = await getLocations(warehouseId)
      setLocationsMap((prev) => ({ ...prev, [warehouseId]: res.data }))
    } catch (e: any) {
      message.error('加载库位失败: ' + (e.response?.data?.message || e.message))
    }
  }

  const updateItem = (index: number, patch: Partial<OutboundItem>) => {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...patch } : it)))
  }

  const addItem = () => {
    setItems((prev) => [
      ...prev,
      { productId: undefined, warehouseId: undefined, locationCode: undefined, quantity: 1 },
    ])
  }

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index))
  }

  const handleWarehouseChange = (index: number, warehouseId: number) => {
    // 切换仓库后清空已选库位，重新加载该仓库库位
    updateItem(index, { warehouseId, locationCode: undefined })
    loadLocations(warehouseId)
  }

  const handleSubmit = async () => {
    if (!customerName.trim()) {
      message.warning('请输入客户名称')
      return
    }
    if (items.length === 0) {
      message.warning('请添加出库明细')
      return
    }
    for (let i = 0; i < items.length; i++) {
      const it = items[i]
      if (!it.productId) {
        message.warning(`第 ${i + 1} 行：请选择商品`)
        return
      }
      if (!it.locationCode) {
        message.warning(`第 ${i + 1} 行：请选择库位`)
        return
      }
      if (!it.quantity || it.quantity < 1) {
        message.warning(`第 ${i + 1} 行：数量必须大于 0`)
        return
      }
    }

    setSubmitting(true)
    try {
      const res = await createOutboundOrder({
        customerName: customerName.trim(),
        items: items.map((it) => ({
          productId: it.productId!,
          quantity: it.quantity,
          locationCode: it.locationCode!,
        })),
      })
      message.success(`出库单创建成功，单号：${res.data.orderNo}`)
      // 提交成功后清空表单
      setCustomerName('')
      setItems([])
    } catch (e: any) {
      message.error(e.response?.data?.message || e.message || '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h3> 出库管理</h3>

      <div style={{ marginBottom: 16 }}>
        <Input
          placeholder="请输入客户名称"
          value={customerName}
          onChange={(e) => setCustomerName(e.target.value)}
          style={{ width: 300 }}
          maxLength={200}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={addItem} style={{ marginLeft: 12 }}>
          添加明细
        </Button>
      </div>

      {items.length === 0 && (
        <div style={{ padding: 24, color: '#999', background: '#fff', borderRadius: 8 }}>
          请点击"添加明细"按钮添加出库商品
        </div>
      )}

      {items.map((item, index) => (
        <div
          key={index}
          style={{
            marginBottom: 12,
            padding: 16,
            background: '#fff',
            borderRadius: 8,
            display: 'flex',
            gap: 12,
            alignItems: 'center',
            flexWrap: 'wrap',
          }}
        >
          <span style={{ color: '#999', width: 48 }}>{index + 1}</span>
          <Select
            placeholder="选择商品"
            showSearch
            allowClear
            style={{ width: 220 }}
            value={item.productId}
            onChange={(v) => updateItem(index, { productId: v })}
            options={productOptions(products)}
            optionFilterProp="label"
            filterOption={(input, option) =>
              (option?.label as string).toLowerCase().includes(input.toLowerCase())
            }
          />
          <Select
            placeholder="选择仓库"
            allowClear
            style={{ width: 150 }}
            value={item.warehouseId}
            onChange={(v) => v && handleWarehouseChange(index, v)}
            options={warehouses.map((w) => ({ label: w.name, value: w.id }))}
          />
          <Select
            placeholder="选择库位"
            allowClear
            style={{ width: 170 }}
            value={item.locationCode}
            onChange={(v) => updateItem(index, { locationCode: v })}
            disabled={!item.warehouseId}
            options={(locationsMap[item.warehouseId!] || []).map((l) => ({
              label: l.code,
              value: l.code,
            }))}
          />
          <InputNumber
            placeholder="数量"
            min={1}
            precision={0}
            value={item.quantity}
            onChange={(v) => updateItem(index, { quantity: v || 0 })}
            style={{ width: 100 }}
          />
          <Button danger icon={<DeleteOutlined />} onClick={() => removeItem(index)} />
        </div>
      ))}

      {items.length > 0 && (
        <Button type="primary" size="large" loading={submitting} onClick={handleSubmit}>
          提交出库单
        </Button>
      )}
    </div>
  )
}
