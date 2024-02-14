import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-quartz.css'
import 'bootstrap/dist/css/bootstrap.min.css'
import { Provider } from 'react-redux'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { filtersStore } from './components/StateManagement'
import Home from './pages/Home'
import NoPage from './pages/NoPage'
import Portfolio from './pages/Portfolio'
import Trading from './pages/Trading'
import LogIn from './pages/LogIn'
import SignUp from './pages/SignUp'

const darkTheme = createTheme({
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarColor: '#6b6b6b #2b2b2b',
          '&::-webkit-scrollbar, & *::-webkit-scrollbar': {
            backgroundColor: '#2b2b2b',
          },
          '&::-webkit-scrollbar-thumb, & *::-webkit-scrollbar-thumb': {
            borderRadius: 8,
            backgroundColor: '#6b6b6b',
            minHeight: 24,
            border: '3px solid #2b2b2b',
          },
          '&::-webkit-scrollbar-thumb:focus, & *::-webkit-scrollbar-thumb:focus':
            {
              backgroundColor: '#959595',
            },
          '&::-webkit-scrollbar-thumb:active, & *::-webkit-scrollbar-thumb:active':
            {
              backgroundColor: '#959595',
            },
          '&::-webkit-scrollbar-thumb:hover, & *::-webkit-scrollbar-thumb:hover':
            {
              backgroundColor: '#959595',
            },
          '&::-webkit-scrollbar-corner, & *::-webkit-scrollbar-corner': {
            backgroundColor: '#2b2b2b',
          },
        },
      },
    },
  },
  palette: {
    mode: 'dark',
  },
})

function App() {
  return (
    <div className="App">
      <Provider store={filtersStore}>
        <ThemeProvider theme={darkTheme}>
          <CssBaseline />
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/trading" element={<Trading />} />
              <Route path="portfolio" element={<Portfolio />} />
              <Route path="/sign-in" element={<LogIn />} />
              <Route path="/sign-up" element={<SignUp />} />
              <Route path="*" element={<NoPage />} />
            </Routes>
          </BrowserRouter>
        </ThemeProvider>
      </Provider>
    </div>
  )
}

export default App
