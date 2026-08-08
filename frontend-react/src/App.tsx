import { Layout, Menu } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { AppstoreOutlined, InboxOutlined, ImportOutlined, ExportOutlined } from '@ant-design/icons'

const { Header, Content } = Layout

function App() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { key: '/products', icon: <AppstoreOutlined />, label: '商品管理' },
    { key: '/inventory', icon: <InboxOutlined />, label: '库存查询' },
    { key: '/inbound', icon: <ImportOutlined />, label: '入库管理' },
    { key: '/outbound', icon: <ExportOutlined />, label: '出库管理' },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', padding: '0 24px' }}>
        <h2 style={{ color: '#fff', margin: 0, marginRight: 40 }}> WMS 仓储管理系统</h2>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ flex: 1, minWidth: 0 }}
        />
      </Header>
      <Content style={{ padding: 24, background: '#f5f5f5' }}>
        <Outlet />
      </Content>
    </Layout>
  )
}

export default App
