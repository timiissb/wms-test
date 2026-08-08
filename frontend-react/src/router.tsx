import { createBrowserRouter, Navigate } from 'react-router-dom'
import App from './App'
import ProductsPage from './pages/ProductsPage'
import InventoryPage from './pages/InventoryPage'
import InboundPage from './pages/InboundPage'
import OutboundPage from './pages/OutboundPage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/products" replace /> },
      { path: 'products', element: <ProductsPage /> },
      { path: 'inventory', element: <InventoryPage /> },
      { path: 'inbound', element: <InboundPage /> },
      { path: 'outbound', element: <OutboundPage /> },
    ],
  },
])

export default router
