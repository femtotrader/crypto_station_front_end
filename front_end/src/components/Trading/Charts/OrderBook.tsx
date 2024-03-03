import { Typography } from '@mui/material'
import HighchartsReact, {
  HighchartsReactRefObject,
} from 'highcharts-react-official'
import Highcharts from 'highcharts/highstock'
import { useEffect, useRef, useState } from 'react'
import { OrderBookData } from '../../DataManagement'
import { CHART_HEIGHT } from './common'

interface BookChartProps {
  data: OrderBookData
  pair: string
  selectedOrder: [string, string, string]
  pairScoreDetails: any
}

export function OrderBookChart(props: BookChartProps) {
  const orderBookChartRef = useRef<HighchartsReactRefObject>(null)
  const bidAskFontSize = '13px'
  const [bid, setBid] = useState(props.data.bid[0][1])
  const [ask, setAsk] = useState(props.data.ask[0][1])
  const [spread, setSpread] = useState(0)
  const [chartOptions] = useState<any>({
    boost: {
      useGPUTranslations: true,
    },
    tooltip: {
      enabled: false,
    },
    xAxis: [
      {
        minRange: 0,
        visible: false,
        type: 'linear',
        labels: { enabled: false },
        snap: false,
        events: {
          afterSetExtremes: afterSetXExtremes,
        },
        tooltip: {
          enabled: false,
        },
      },
    ],
    yAxis: [
      {
        visible: true,
        labels: {
          enabled: false,
        },
        resize: {
          enabled: true,
        },
        title: { text: '' },
        lineWidth: 0,
        gridLineWidth: 0,
        tooltip: {
          enabled: true,
        },
      },
    ],
    title: {
      text: 'order book',
      style: {
        fontSize: 0,
      },
    },
    series: [
      {
        data: [],
        name: 'Bids',
        yAxis: 0,
        color: 'green',
        fillColor: {
          linearGradient: [300, 0, 0, 300],
          stops: [
            [0, 'rgba(0, 150, 0, 1)'],
            [1, 'rgba(0, 0, 0, 0)'],
          ],
        },
        type: 'area',
      },
      {
        data: [],
        name: 'Asks',
        yAxis: 0,
        color: 'red',
        fillColor: {
          linearGradient: [0, 0, 300, 0],
          stops: [
            [0, 'rgba(0, 0, 0, 0)'],
            [1, 'rgba(150, 0, 0, 1'],
          ],
        },
        threshold: Infinity,
        type: 'area',
      },
    ],
    stockTools: {
      gui: {
        enabled: false,
      },
    },
    navigation: {
      bindingsClassName: 'book-chart',
    },
    chart: {
      backgroundColor: 'transparent',
      height: CHART_HEIGHT - 215,
      animation: false,
      zooming: {
        mouseWheel: { enabled: true, type: 'x' },
      },
    },
    legend: {
      enabled: false,
    },
    plotOptions: {
      series: {
        point: {
          events: {
            mouseOver: handleHover,
            mouseOut: handleOut,
          },
        },
      },
    },
    credits: { enabled: false },
  })

  function getOverSidePrice(price: number) {
    const bid = props.data.bid[0][1]
    const ask = props.data.ask[0][1]
    if (price >= ask) {
      const distance = price / ask - 1
      return ['bid', bid - distance * bid]
    } else if (bid >= price) {
      const distance = bid / price - 1
      return ['ask', distance * ask + ask]
    }
  }

  function handleOut() {
    if (orderBookChartRef.current) {
      setBid(props.data.bid[0][1])
      setAsk(props.data.ask[0][1])
      setSpread(props.data.ask[0][1] / props.data.bid[0][1] - 1)
      orderBookChartRef.current.chart.series[0].yAxis.removePlotLine(
        'ask-book-hover-line',
      )
      orderBookChartRef.current.chart.series[0].yAxis.removePlotLine(
        'bid-book-hover-line',
      )
      orderBookChartRef.current.chart.series[0].yAxis.removePlotLine(
        'central-book-hover-line',
      )
    }
  }

  function handleHover(this: any) {
    const overSidePrice = getOverSidePrice(this.y)
    const bids = props.data.bid
    const bid = bids[0][1]
    const ask = props.data.ask[0][1]
    if (orderBookChartRef.current) {
      handleOut()
      if (overSidePrice !== undefined) {
        const hoverBid = Math.max(
          bids[bids.length - 1][1],
          overSidePrice[0] === 'bid' ? overSidePrice[1] : this.y,
        )
        const hoverAsk = overSidePrice[0] === 'ask' ? overSidePrice[1] : this.y
        const spread = hoverAsk / hoverBid - 1
        setBid(Math.max(0, hoverBid))
        setAsk(hoverAsk)
        setSpread(spread)

        orderBookChartRef.current.chart.series[0].yAxis.addPlotLine({
          color: 'red',
          value: hoverAsk,
          dashStyle: 'Dot',
          id: 'ask-book-hover-line',
        })
        orderBookChartRef.current.chart.series[0].yAxis.addPlotLine({
          color: 'green',
          value: hoverBid,
          dashStyle: 'Dot',
          id: 'bid-book-hover-line',
        })
        orderBookChartRef.current.chart.series[0].yAxis.addPlotLine({
          color: 'white',
          value: (ask + bid) / 2,
          width: 0,
          id: 'central-book-hover-line',
        })
      }
    }
  }

  useEffect(() => {
    const chart = orderBookChartRef!.current!.chart
    if (chart) {
      if (chart.xAxis[0].max) {
        chart.xAxis[0].setExtremes(0, chart.xAxis[0].max)
      }
      chart.series[0].setData(props.data.bid)
      chart.series[1].setData(props.data.ask)
    }
  }, [props.data])

  useEffect(() => {
    if (orderBookChartRef.current && orderBookChartRef.current.chart) {
      orderBookChartRef.current.chart.zoomOut()
    }
  }, [props.pair])

  function afterSetXExtremes(this: any, e: any) {
    this.setExtremes(0, this.max)
  }

  return (
    <div style={{ marginTop: '50px', marginLeft: '-40px' }}>
      <Typography display={'flex'} justifyContent={'center'}>
        <span
          style={{ color: 'green', fontSize: bidAskFontSize }}
        >{`Bid: ${bid.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}</span>
        &nbsp;&nbsp;
        <span
          style={{ fontSize: bidAskFontSize }}
        >{`Spread: ${(spread * 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}%`}</span>
        &nbsp;&nbsp;
        <span
          style={{ color: 'red', fontSize: bidAskFontSize }}
        >{`Ask: ${ask.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}</span>
      </Typography>

      <HighchartsReact
        highcharts={Highcharts}
        options={chartOptions}
        ref={orderBookChartRef}
      />
    </div>
  )
}
