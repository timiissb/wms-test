/**
 * 商品管理页 — 参考实现
 *
 * 展示了：
 * - 列表 + 搜索
 * - 新增 / 编辑弹窗 (Modal)
 * - 删除确认
 * - 前端分页
 *
 * ️ BUG 预埋点：编辑后返回列表时页码重置为第1页
 *   候选人需要在任务3中修复此问题
 */
import { useState, useEffect, useMemo } from 'react'
import { Table, Button, Input, Space, Modal, Form, message, Popconfirm } from 'antd'
import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { getProducts, createProduct, updateProduct, deleteProduct, type Product } from '@/api'

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  // 每页条数也可切换（10/20/50/100），存 state 而非常量
  const [pageSize, setPageSize] = useState(10)
  const [form] = Form.useForm()

  const loadProducts = async () => {
    setLoading(true)
    try {
      const res = await getProducts(keyword || undefined)
      setProducts(res.data)
    } catch (e: any) {
      message.error('加载失败: ' + (e.response?.data?.message || e.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadProducts() }, [])

  const pagedProducts = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return products.slice(start, start + pageSize)
  }, [products, currentPage, pageSize])

  const handleAdd = () => {
    setEditingProduct(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = (product: Product) => {
    setEditingProduct(product)
    form.setFieldsValue(product)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingProduct) {
        await updateProduct(editingProduct.id, { name: values.name, unit: values.unit })
        message.success('更新成功')
        // 编辑是就地修改，数据条数不变，应停留在当前页，不重置页码
      } else {
        await createProduct({ name: values.name, sku: values.sku, unit: values.unit })
        message.success('创建成功')
        // 新增商品追加在列表末尾，回到第 1 页便于从首页查看
        setCurrentPage(1)
      }
      setModalOpen(false)
      await loadProducts()
    } catch (e: any) {
      if (e.response) message.error(e.response?.data?.message || '操作失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteProduct(id)
      message.success('删除成功')
      // 删除后若当前页已空（删掉了最后一页的最后一条），页码回退，避免停留在空页
      const maxPage = Math.max(1, Math.ceil((products.length - 1) / pageSize))
      if (currentPage > maxPage) setCurrentPage(maxPage)
      await loadProducts()
    } catch (e: any) {
      message.error(e.response?.data?.message || '删除失败')
    }
  }

  const columns: ColumnsType<Product> = [
    { title: 'ID', dataIndex: 'id', width: 80 },
    { title: '商品名称', dataIndex: 'name' },
    { title: 'SKU', dataIndex: 'sku', width: 150 },
    { title: '单位', dataIndex: 'unit', width: 80 },
    {
      title: '操作', width: 180,
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除该商品吗？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索商品名称/SKU..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={loadProducts}
          style={{ width: 300 }}
          allowClear
        />
        <Button type="primary" onClick={loadProducts}>搜索</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增商品</Button>
      </div>

      <Table
        columns={columns}
        dataSource={pagedProducts}
        rowKey="id"
        loading={loading}
        pagination={{
          current: currentPage,
          pageSize,
          total: products.length,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50, 100],
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, ps) => {
            // 翻页或切换每页条数：同时更新页码与条数（切换条数时 AntD 重置回第 1 页）
            setCurrentPage(page)
            setPageSize(ps)
          },
        }}
      />

      <Modal
        title={editingProduct ? '编辑商品' : '新增商品'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="商品名称" rules={[{ required: true, max: 200 }]}>
            <Input />
          </Form.Item>
          {!editingProduct && (
            <Form.Item name="sku" label="SKU" rules={[{ required: true, max: 50 }]}>
              <Input />
            </Form.Item>
          )}
          <Form.Item name="unit" label="单位" initialValue="个">
            <Input maxLength={20} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
