/**
 * ============================================
 *  库存查询页 — 任务2 实现 + 任务C 性能优化
 * ============================================
 *
 * 优化方案（任务C）：
 * 1. 后端分页：只请求当前页（page/pageSize），500+ 条数据也只传输一页
 * 2. 防抖搜索：keyword 停止输入 500ms 后才查询，避免每次按键请求后端
 * 3. 状态同步 URL：keyword / warehouseId / page 写入 URL query，
 *    刷新或返回列表时保持筛选条件与页码，不跳回第 1 页
 *
 * 参考 ProductsPage.tsx 的实现风格
 */
import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Table, Input, Select, Button, message } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'
import { getInventory, type InventoryItem, getWarehouses, type Warehouse } from '@/api'

const pageSize = 20
// 库存低于该值的行红色高亮
const LOW_STOCK_THRESHOLD = 10

export default function InventoryPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  // 从 URL query 恢复筛选/分页状态（刷新、返回后保持）
  const [keyword, setKeyword] = useState(searchParams.get('keyword') ?? '')
  const [warehouseId, setWarehouseId] = useState<number | undefined>(
    searchParams.get('warehouseId') ? Number(searchParams.get('warehouseId')) : undefined
  )
  const [page, setPage] = useState<number>(Math.max(1, Number(searchParams.get('page') || 1)))
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<InventoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  // 用于跳过首次渲染时防抖 effect 的重复查询
  const isFirstRender = useRef(true)

  // 将筛选/分页状态同步到 URL query（replace 避免历史堆栈膨胀）
  const syncUrl = (kw: string, whId: number | undefined, p: number) => {
    const params: Record<string, string> = {}
    if (kw) params.keyword = kw
    if (whId !== undefined) params.warehouseId = String(whId)
    if (p > 1) params.page = String(p)
    setSearchParams(params, { replace: true })
  }

  const fetchInventory = async (kw: string, whId: number | undefined, targetPage = 1) => {
    setLoading(true)
    syncUrl(kw, whId, targetPage)
    try {
      const res = await getInventory({
        keyword: kw || undefined,
        warehouseId: whId,
        page: targetPage,
        pageSize,
      })
      setData(res.data.list)
      setTotal(res.data.total)
      setPage(targetPage)
    } catch (e: any) {
      message.error('加载库存失败: ' + (e.response?.data?.message || e.message))
    } finally {
      setLoading(false)
    }
  }

  // 首次加载：仓库列表 + 按 URL 初始状态查询
  useEffect(() => {
    const loadWarehouses = async () => {
      try {
        const res = await getWarehouses()
        setWarehouses(res.data)
      } catch (e: any) {
        message.error('加载仓库失败: ' + (e.response?.data?.message || e.message))
      }
    }
    loadWarehouses()
    fetchInventory(keyword, warehouseId, page)
  }, [])

  // keyword 输入防抖：停止输入 500ms 后自动查询（重置到第 1 页）
  useEffect(() => {
    if (isFirstRender.current) return
    const timer = setTimeout(() => {
      fetchInventory(keyword, warehouseId, 1)
    }, 500)
    return () => clearTimeout(timer)
  }, [keyword])

  // 标记首次渲染完成（在防抖 effect 首次触发前置为 false）
  useEffect(() => {
    isFirstRender.current = false
  }, [])

  const handleWarehouseChange = (v: number | undefined) => {
    setWarehouseId(v)
    // 下拉筛选是明确动作，立即查询
    fetchInventory(keyword, v, 1)
  }

  const isLowStock = (record: InventoryItem) => record.quantity < LOW_STOCK_THRESHOLD

  const columns: ColumnsType<InventoryItem> = [
    { title: '商品名称', dataIndex: 'productName' },
    { title: 'SKU', dataIndex: 'sku', width: 150 },
    { title: '库位编码', dataIndex: 'locationCode', width: 150 },
    { title: '仓库', dataIndex: 'warehouseName', width: 120 },
    {
      title: '库存数量',
      dataIndex: 'quantity',
      width: 100,
      render: (qty: number, record) => (
        <span style={{ color: isLowStock(record) ? '#ff4d4f' : undefined, fontWeight: 600 }}>
          {qty}
        </span>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      width: 180,
      render: (t: string) => (t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
  ]

  return (
    <div>
      <h3> 库存查询</h3>

      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索商品名称/SKU..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          allowClear
          style={{ width: 300 }}
          onPressEnter={() => fetchInventory(keyword, warehouseId, 1)}
        />
        <Select
          placeholder="选择仓库"
          allowClear
          style={{ width: 200 }}
          value={warehouseId}
          onChange={handleWarehouseChange}
          options={warehouses.map((w) => ({ label: w.name, value: w.id }))}
        />
        <Button type="primary" onClick={() => fetchInventory(keyword, warehouseId, 1)}>
          查询
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        rowKey={(record) => `${record.productId}-${record.locationCode}`}
        loading={loading}
        onRow={(record) =>
          isLowStock(record) ? { style: { background: '#fff1f0' } } : {}
        }
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: (p) => fetchInventory(keyword, warehouseId, p),
          showTotal: (t) => `共 ${t} 条`,
        }}
        locale={{ emptyText: '暂无库存数据，请先完成入库操作' }}
      />
    </div>
  )
}
