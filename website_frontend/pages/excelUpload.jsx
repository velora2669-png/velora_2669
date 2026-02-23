"use client";

import { MapContainer, TileLayer } from "react-leaflet";
import * as XLSX from "xlsx";
import { motion } from "framer-motion"; 
import {
  Route,
  Truck,
  BarChart3,
  Clock,
  Users,
  Shield,
  Upload,
  Settings,
  Rocket,
} from "lucide-react";
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

// Updated Sage Green Palette
const ROUTE_COLORS = [
  "#ecf1e6", "#b9c3b4", "#97a391", "#838f77", "#687664", "#4a5846", "#4a5846"
];

// Animation Variants
const fadeInUp = {
  initial: { opacity: 0, y: 30 },
  animate: { 
    opacity: 1, 
    y: 0,
    transition: { 
      duration: 1.2, 
      ease: [0.22, 1, 0.36, 1] 
    }
  }
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.3 
    }
  }
};

const PREDEFINED_TESTCASES = [
  "TestCase_TC01.xlsx",
  "TestCase_TC02.xlsx",
  "TestCase_TC03.xlsx",
  "TestCase_TC04.xlsx",
];

export default function ExcelUpload() {
  const [file, setFile] = useState(null);
  const [selectedTestcase, setSelectedTestcase] = useState("");
  const [mode, setMode] = useState("testcase"); // "testcase" or "upload"
  const navigate = useNavigate();

const upload = async (e) => {
  e.preventDefault();

  let arrayBuffer;
  let actualFile = file;

  if (mode === "upload") {
    if (!file) {
      alert("Please select an Excel file");
      return;
    }

    arrayBuffer = await file.arrayBuffer();
  } else {
    if (!selectedTestcase) {
      alert("Please select a testcase");
      return;
    }

    try {
      // fetch testcase from public folder
      const response = await fetch(`/testcases/${selectedTestcase}`);

      if (!response.ok) {
        alert("Testcase file not found");
        return;
      }

      arrayBuffer = await response.arrayBuffer();

      // optional: create File object so rest of app works same
      actualFile = new File([arrayBuffer], selectedTestcase, {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });

    } catch (err) {
      console.error(err);
      alert("Failed to load testcase");
      return;
    }
  }

  // READ EXCEL (same logic for both modes)
  const data = new Uint8Array(arrayBuffer);
  const workbook = XLSX.read(data, { type: "array" });

  const sheet = workbook.Sheets["metadata"];

  if (!sheet) {
    alert("metadata sheet not found");
    return;
  }

  const json = XLSX.utils.sheet_to_json(sheet);

  const allowMapsRow = json.find(
    (row) => row.key === "allow_external_maps"
  );

  if (!allowMapsRow) {
    alert("allow_external_maps not found");
    return;
  }

  const allowMaps =
    allowMapsRow.value === true ||
    allowMapsRow.value === "TRUE" ||
    allowMapsRow.value === "true";

  // Navigate with testcase context when applicable
  const statePayload =
    mode === "testcase"
      ? { file: actualFile, testcaseName: selectedTestcase }
      : { file: actualFile };

  if (allowMaps) {
    navigate("/tempMap", { state: statePayload });
  } else {
    navigate("/nomap", { state: statePayload });
  }
};

  return (
    <div className="relative w-full min-h-screen overflow-hidden font-sans z-10 bg-white/40 font-">
          {/* Map Section */}
          {/* <section className="relative w-full h-screen overflow-hidden"> */}
          <div className="relative z-10 w-screen mx-auto px-6 py-8 bg-white/40 ">
            <div className="fixed inset-0 z-0 ">
              
              <MapContainer
                center={[12.9612, 77.5946]}
                zoom={15}
                zoomControl={true}
                scrollWheelZoom={false}
                className="w-full h-full"
              >
                <TileLayer
                  url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png"
                  attribution="&copy; OpenStreetMap contributors &copy; CARTO"
                />
             
                       </MapContainer>
                       
            </div>
            {/* <div className="fixed inset-0 z-[1] bg-white/60 backdrop-blur-[1px]" />
            <div className="absolute inset-0 z-10 bg-gradient-to-b from-white/20 via-white/10 to-white/30" /> */}
    
            {/* Hero Content */}
            <motion.div 
              initial="initial"
              animate="animate"
              variants={staggerContainer}
              className="relative z-20 flex flex-col items-center justify-start min-h-[50vh] text-center px-6 pt-6"
            >
              {/* Status pill */}
              <motion.div variants={fadeInUp} className="mb-6">
                <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full 
                  bg-white border border-slate-200 text-slate-700 text-sm font-medium shadow-sm">
                  <span className="w-2 h-2 bg-[#97a391] rounded-full animate-pulse" />
                  Optimization Engine Active
                </span>
              </motion.div>
    
              {/* Heading */}
              <motion.h1 variants={fadeInUp} className="text-4xl md:text-6xl font-bold text-[#4a5846] leading-tight max-w-4xl">
                Optimizing the <span style={{ color: ROUTE_COLORS[3] }}>Future</span> of the Commute
              </motion.h1>
    
              {/* Subtext */}
              <motion.p variants={fadeInUp} className="mt-6 text-lg md:text-xl text-[#687664] max-w-2xl">
                Intelligent fleet routing that cuts costs, saves time, and simplifies
                employee transportation — all from a single upload.
              </motion.p>
    
              {/* Buttons */}
              <motion.div variants={fadeInUp} className="mt-6 flex gap-4">
<div className="flex items-center justify-center bg-transparent">
  <div className="bg-transparent p-8 rounded-2xl  w-full  text-center">
    
    {/* <h2 className="text-2xl font-semibold mb-2 text-gray-500">
      Upload Excel File
    </h2> */}

<form 
  onSubmit={upload} 
  className="
    w-full max-w-2xl 
    mx-auto
    px-8 py-4
    mt-2
    flex flex-col
    gap-4
    /* Gray Border and Background styling */
    border border-gray-300
    rounded-2xl
    bg-white/50
    backdrop-blur-md
  "
>
  {/* Mode Selection */}
  <div className="flex gap-4 w-full">
    <button
      type="button"
      onClick={() => setMode("testcase")}
      className={`
        flex-1
        py-3 px-6
        rounded-xl
        font-semibold
        transition duration-200
        border
        whitespace-nowrap
        ${
          mode === "testcase"
            ? "bg-[#4a5846] text-white border-[#4a5846]"
            : "bg-gray-100/80 text-gray-500 border-gray-200 hover:bg-gray-200"
        }
      `}
    >
      Use Testcase
    </button>

    <button
      type="button"
      onClick={() => setMode("upload")}
      className={`
        flex-1
        py-3 px-6
        rounded-xl
        font-semibold
        transition duration-200
        border
        whitespace-nowrap
        ${
          mode === "upload"
            ? "bg-[#4a5846] text-white border-[#4a5846]"
            : "bg-gray-100/80 text-gray-500 border-gray-200 hover:bg-gray-200"
        }
      `}
    >
      Upload File
    </button>
  </div>

  {/* Input Section */}
  <div className="flex flex-col gap-1.5 w-full min-h-[85px] items-center">
    <label className="text-xs font-bold text-gray-500 uppercase tracking-widest">
      {mode === "testcase" ? "Select Testcase" : "Choose Excel File"}
    </label>

    <div className="relative h-[56px] w-full">
      {mode === "testcase" ? (
        <select
          value={selectedTestcase}
          onChange={(e) => setSelectedTestcase(e.target.value)}
          className="
            absolute inset-0
            w-full h-full
            px-6
            rounded-xl
            border border-gray-300
            focus:outline-none
            focus:ring-2 focus:ring-[#4a5846]
            focus:border-[#4a5846]
            transition duration-200
            bg-white/90
            text-gray-600
          "
        >
          <option value="">-- Select a testcase --</option>
          {PREDEFINED_TESTCASES.map((tc) => (
            <option key={tc} value={tc}>
              {tc.replace(".xlsx", "")}
            </option>
          ))}
        </select>
      ) : (
        <input
          type="file"
          accept=".xls,.xlsx"
          onChange={(e) => setFile(e.target.files[0])}
          className="
            absolute inset-0
            w-full h-full
            text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-lg file:border-0
            file:text-sm file:font-semibold
            file:bg-gray-100 file:text-gray-600
            hover:file:bg-gray-200
            cursor-pointer
            border border-gray-300
            rounded-xl
            p-2.5
            bg-white/90
            hover:border-gray-400
            transition duration-200
          "
        />
      )}
    </div>
  </div>

  {/* Submit Button & Footer */}
  <div className="w-full flex flex-col gap-2 items-center">
    <motion.button
      type="submit"
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      className="
        w-full max-w-md
        py-4
        rounded-xl
        text-white font-bold
        text-base
        shadow-sm hover:shadow-lg
        transition-all duration-300
      "
      style={{ backgroundColor: ROUTE_COLORS[5] }}
    >
      {mode === "testcase" ? "Run Optimization" : "Upload & Optimize"}
    </motion.button>

    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
      Supported formats: .xls, .xlsx
    </p>
  </div>
</form>

  </div>
  </div>

              </motion.div>
            </motion.div>
          {/* </section> */}
              </div>
          {/* Stats & Features Section */}
          <div className="relative z-10 w-screen mx-auto px-6 py-24 bg-white/50 ">
            
            
    
            {/* Feature Heading */}
            <motion.div 
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <h2 className="text-4xl font-bold mb-4 text-[#4a5846]">
                Everything You Need to <span style={{ color: ROUTE_COLORS[3] }}>Optimize</span>
              </h2>
              <p className="text-[#687664] text-lg max-w-2xl mx-auto">
                A complete suite of tools to transform employee transportation from chaos into clarity.
              </p>
            </motion.div>
    
            {/* Features Grid */}
            <motion.div 
              initial="initial"
              whileInView="animate"
              viewport={{ once: true }}
              variants={staggerContainer}
              className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 m-24 "
            >
              <FeatureCard icon={<Route />} title="Smart Seat Matching" description="Automatically pairs employees with the best vehicle based on seating capacity and their personal preferences" color={ROUTE_COLORS[5]} />
              <FeatureCard icon={<Truck />} title="Fastest Route Planning" description="Creates the most efficient pick-up and drop-off paths to save time and reduce driving distance." color={ROUTE_COLORS[4]} />
              <FeatureCard icon={<BarChart3 />} title=" Schedule Sync" description="Organizes trips around specific employee work hours and vehicle availability times." color={ROUTE_COLORS[3]} />
              <FeatureCard icon={<Clock />} title="Cost Savings " description="Compares your optimized plan against standard taxi prices to show exactly how much money you saved." color={ROUTE_COLORS[2]} />
              <FeatureCard icon={<Users />} title="Easy File Upload" description="Lets you quickly upload an Excel sheet of trip requests and get an optimized plan in seconds." color={ROUTE_COLORS[4]} />
              <FeatureCard icon={<Shield />} title="Trip Map Preview" description="Displays all employee locations and your planned routes clearly on a real-world map." color={ROUTE_COLORS[5]} />
            </motion.div>
    
            {/* How it Works */}
            <div className="text-center mb-16">
              <motion.h3 
                initial={{ y: 20, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                viewport={{ once: true }}
                className="text-3xl font-bold text-[#4a5846]"
              >
                How It <span style={{ color: ROUTE_COLORS[3] }}>Works</span>
                <p className="text-lg text-[#4a5846]">Three simple steps from raw data to optimized routes.</p>
              </motion.h3>
            </div>
    
            <motion.div 
              initial="initial"
              whileInView="animate"
              viewport={{ once: true }}
              variants={staggerContainer}
              className="grid md:grid-cols-3 gap-8 mb-24 text-2xl"
            >
              <StepCard1 number="01" icon={<Upload />} title="Upload Data" color={ROUTE_COLORS[5]} text={"Import your employee locations and fleet details via Excel"}/>
              <StepCard1 number="02" icon={<Settings />} title="Engine Optimizes" color={ROUTE_COLORS[4]} text={"Our engine analyzes constraints, priorities, and routes in real-time."} />
              <StepCard1 number="03" icon={<Rocket />} title="Deploy Routes" color={ROUTE_COLORS[3]} text={"Push optimized routes to drivers and track everything from one dashboard."}/>
            </motion.div>
    
            {/* Final CTA */}
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              whileInView={{ scale: 1, opacity: 1 }}
              viewport={{ once: true }}
              className="flex justify-center"
            >
              <div className="bg-white border border-slate-200 rounded-3xl shadow-xl px-12 py-12 text-center max-w-2xl w-full">
                <BarChart3 className="mx-auto mb-6 w-12 h-12" style={{ color: ROUTE_COLORS[5] }} />
                <h4 className="text-3xl font-bold mb-4 text-[#4a5846]">Ready to optimize your fleet?</h4>
                <p className="text-[#687664] mb-8 text-lg">
                  Upload your data and see optimized routes, cost savings, and fleet utilization instantly.
                </p>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                  className="text-white px-10 py-4 rounded-xl font-bold shadow-lg transition-all"
                  style={{ backgroundColor: ROUTE_COLORS[5] }}
                >
                  Get Started Now
                </motion.button>
              </div>
            </motion.div>
          </div>

        </div>
  );
}

/* --- Animated Components --- */

function StatCard({ value, label, color }) {
  return (
    <motion.div 
      variants={fadeInUp}
      whileHover={{ y: -5 }}
      className="bg-white border border-slate-200 rounded-2xl p-8 text-center shadow-sm hover:shadow-md transition-all"
    >
      <div className="text-4xl font-bold mb-2" style={{ color }}>{value}</div>
      <div className="text-slate-500 font-medium">{label}</div>
    </motion.div>
  );
}

function FeatureCard({ icon, title, description, color }) {
  return (
    <motion.div 
      variants={fadeInUp}
      whileHover={{ y: -8 }}
      className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm hover:shadow-xl transition-all group"
    >
      <div 
        className="w-6 h-6 flex items-center justify-center rounded-xl mb-6 transition-transform group-hover:rotate-12"
        style={{ backgroundColor: color + "20", color }}
      >
        {icon}
      </div>
      <h4 className="text-xl font-bold mb-3 text-[#4a5846]">{title}</h4>
      <p className="text-slate-600 leading-relaxed">{description}</p>
    </motion.div>
  );
}

function StepCard({ number, icon, title, color }) {
  return (
    <motion.div 
      variants={fadeInUp}
      whileHover={{ scale: 1.02 }}
      className="relative bg-white border border-slate-200 rounded-2xl p-10 shadow-sm overflow-hidden"
    >
      <div className="absolute -top-2 -right-2 text-7xl font-black text-slate-50 select-none">
        {number}
      </div>
      <div style={{ color }} className="mb-6 scale-125 origin-left">
        {icon}
      </div>
      <div className="font-bold text-xl relative z-10 text-[#4a5846]">{title}</div>
    </motion.div>
  );
}

function StepCard1({ number, icon, title, color,text}) {
  return (
    <motion.div
      variants={fadeInUp}
      whileHover={{ y: -6 }}
      className="relative p-10 text-center"
    >
      {/* BIG BACKGROUND NUMBER */}
      <div
        className="absolute inset-0 flex items-center justify-center select-none pointer-events-none"
        style={{
          zIndex: 100,
        }}
      >
        <span
          style={{
            color,
            opacity: 0.18,
            fontSize: "140px",
            fontWeight: "900",
            lineHeight: "1",
          }}
        >
          {parseInt(number)}
        </span>
      </div>

      {/* FOREGROUND CONTENT */}
      <div className="relative z-10">
        {/* <div style={{ color }} className="mb-4 flex justify-center">
          {icon}
        </div> */}
        <br>
        </br>
        <br></br>
        <br></br>
        <br></br>
        

        <h4 className="text-xl font-bold text-[#4a5846]">
          {title}
        </h4>
        <p className="text-sm  text-[#4a5846]">{text}</p>
      </div>
    </motion.div>
  );
}