import { CircularProgress } from '@mui/material'
import {
  ColDef,
  GridReadyEvent,
  RowClickedEvent,
  SideBarDef,
} from 'ag-grid-community'
import 'ag-grid-enterprise'
import { AgGridReact } from 'ag-grid-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Container } from 'react-bootstrap'
import { useDispatch, useSelector } from 'react-redux'
import { type Order, type tradingDataDef } from '../DataManagement'
import { filterSlice, type FilterState } from '../StateManagement'
import './tables.css'

interface TableProps {
  orders: Order[]
}

function formatTimeStamp(originalDate: any) {
  let formattedDate = originalDate.substring(0, 19)
  formattedDate = formattedDate.replace('T', ' ')
  return formattedDate
}

function OrderTable({ orders }: TableProps) {
  const gridRef = useRef<AgGridReact<Order[]>>(null)
  const dispatch = useDispatch()
  const filterState = useSelector(
    (state: { filters: FilterState }) => state.filters,
  )
  const [pair, selectedOrder] = useMemo(
    () => [filterState.pair, filterState.selectedOrder],
    [filterState.pair, filterState.selectedOrder],
  )

  const [colDefs, setColDefs] = useState<ColDef<Order>[]>([])

  function setDefaultGridSettings() {
    if (gridRef.current && gridRef.current.api) {
      gridRef.current.api.applyColumnState({
        state: [{ colId: 'order_creation_tmstmp', sort: 'desc' }],
        defaultState: { sort: null },
      })
      gridRef.current.api
        .setColumnFilterModel('asset_id', { values: [pair] })
        .then(() => {
          gridRef.current!.api.onFilterChanged()
        })
    }
  }

  useEffect(() => {
    setColDefs([
      { field: 'order_creation_tmstmp' },
      { field: 'trading_env', hide: true },
      { field: 'asset_id', filter: 'agSetColumnFilter' },
      {
        field: 'order_side',
        cellRenderer: (params: { value: string }) => {
          const action = params.value.toLowerCase()
          let cellClass = ''
          if (action === 'buy') {
            cellClass = 'buy-cell'
          } else if (action === 'sell') {
            cellClass = 'sell-cell'
          }
          return <span className={cellClass}>{action}</span>
        },
      },
      { field: 'trading_type', hide: true },
      { field: 'order_status' },
      {
        field: 'fill_pct',
        valueFormatter: (params) => (params.value * 100).toFixed(2) + '%',
      },
      { field: 'order_volume' },
      { field: 'order_price' },
    ])
    setDefaultGridSettings()
  }, [orders])

  const handleClick = (clickedOrder: RowClickedEvent<Order, any>) => {
    const order = clickedOrder.data
    if (order !== undefined) {
      if (order.order_id !== selectedOrder[2]) {
        dispatch(
          filterSlice.actions.setSelectedOrder([
            order.order_creation_tmstmp,
            order.order_price,
            order.order_id,
          ]),
        )
        if (pair !== order['asset_id']) {
          dispatch(filterSlice.actions.setPair(order.asset_id))
        }
      } else {
        dispatch(filterSlice.actions.setSelectedOrder(['', '', '']))
      }
    }
  }

  const onGridReady = useCallback((event: GridReadyEvent) => {
    setDefaultGridSettings()
  }, [])

  const defaultColDef = useMemo<ColDef>(() => {
    return {
      flex: 1,
      filter: true,
    }
  }, [])

  const sideBar = useMemo<
    SideBarDef | string | string[] | boolean | null
  >(() => {
    return {
      toolPanels: [
        {
          id: 'columns',
          labelDefault: 'Columns',
          labelKey: 'columns',
          iconKey: 'columns',
          toolPanel: 'agColumnsToolPanel',
          minWidth: 225,
          width: 225,
          maxWidth: 225,
        },
        {
          id: 'filters',
          labelDefault: 'Filters',
          labelKey: 'filters',
          iconKey: 'filter',
          toolPanel: 'agFiltersToolPanel',
          minWidth: 180,
          maxWidth: 400,
          width: 250,
        },
      ],
      position: 'left',
      defaultToolPanel: 'filters',
      hiddenByDefault: true,
    }
  }, [])

  return orders.length === 0 ? (
    <CircularProgress style={{ marginLeft: '50%', marginTop: '10%' }} />
  ) : (
    <div
      className={'ag-theme-quartz-dark'}
      style={{ width: '100%', height: '180px' }}
    >
      <AgGridReact
        ref={gridRef}
        rowData={orders}
        columnDefs={colDefs}
        defaultColDef={defaultColDef}
        sideBar={sideBar}
        onRowClicked={(r) => handleClick(r)}
        onGridReady={onGridReady}
        rowSelection={'single'}
      />
    </div>
  )
}

function Orders(data: { tradingData: tradingDataDef }) {
  return (
    <Container>
      <OrderTable orders={data.tradingData.orders} />
    </Container>
  )
}

export default Orders
