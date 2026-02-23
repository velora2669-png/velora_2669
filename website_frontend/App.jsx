import React from 'react';
import MapWithOSRM from './pages/MapWithOSRM.jsx';
import ExcelUpload from './pages/excelUpload.jsx';
import Loader from './pages/loader.jsx'
import TempMap from './pages/tempMap.jsx'
import Nomap from './pages/nomap.jsx'
import { Route,Routes } from 'react-router-dom';

function App() {
  return (
    <div className="App">
     <Routes>
        <Route path="/" element={<ExcelUpload />} />
        <Route path="/loader" element={<Loader />} />
        <Route path="/map" element={<MapWithOSRM />} />
        <Route path="/tempmap" element={<TempMap />} />
        <Route path="/nomap" element={<Nomap />} />
      </Routes>
      
    </div>
  );
}

export default App;
