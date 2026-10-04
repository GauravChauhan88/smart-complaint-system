import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000/api";

// Pure SVG Icons (Zero dependency issues with React 19)
const Icons = {
  FileText: () => (
    <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  ShieldAlert: () => (
    <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  Clock: () => (
    <svg className="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  AlertCircle: () => (
    <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  Send: () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
    </svg>
  ),
  CheckCircle: () => (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  Refresh: () => (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  )
};

export default function App() {
  const [complaints, setComplaints] = useState([]);
  const [stats, setStats] = useState({
    total_tickets: 0,
    critical_tickets: 0,
    open_tickets: 0,
    needs_manual_review: 0
  });

  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [complaintText, setComplaintText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState("agent");
  const [backendOnline, setBackendOnline] = useState(true);

  const fetchData = async () => {
    try {
      const resComplaints = await axios.get(`${API_BASE}/complaints`);
      const resStats = await axios.get(`${API_BASE}/stats`);
      
      if (Array.isArray(resComplaints.data)) setComplaints(resComplaints.data);
      if (resStats.data) setStats(resStats.data);
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!complaintText.trim()) return;

    setSubmitting(true);
    try {
      await axios.post(`${API_BASE}/complaints`, {
        customer_name: customerName || "Anonymous Customer",
        customer_email: customerEmail || "customer@example.com",
        text: complaintText
      });
      setComplaintText("");
      setCustomerName("");
      setCustomerEmail("");
      await fetchData();
      setActiveTab("agent");
    } catch {
      alert("Submission failed. Ensure backend is running at http://127.0.0.1:8000");
    } finally {
      setSubmitting(false);
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await axios.patch(`${API_BASE}/complaints/${id}`, { status });
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const parseEntities = (raw) => {
    if (!raw) return {};
    if (typeof raw === "object") return raw;
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  };

  const getUrgencyBadge = (urgency) => {
    const map = {
      Critical: "bg-red-500/10 text-red-400 border border-red-500/30",
      High: "bg-orange-500/10 text-orange-400 border border-orange-500/30",
      Medium: "bg-yellow-500/10 text-yellow-400 border border-yellow-500/30",
      Low: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30",
    };
    return (
      <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${map[urgency] || map.Low}`}>
        {urgency || "Low"}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 font-sans">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {!backendOnline && (
          <div className="bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs px-4 py-2 rounded-lg flex items-center gap-2">
            <Icons.AlertCircle />
            FastAPI backend unreachable. Make sure `uvicorn backend.main:app --port 8000` is active.
          </div>
        )}

        {/* Header */}
        <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-6 border-b border-slate-800 gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              Smart Complaint Triage & Routing System
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Multi-Task DistilBERT NLP Engine with Automated Urgency & Entity Detection
            </p>
          </div>
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1.5 rounded-lg text-sm">
            <button
              onClick={() => setActiveTab("agent")}
              className={`px-4 py-2 rounded-md font-medium transition cursor-pointer ${
                activeTab === "agent" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              Agent Triage Portal
            </button>
            <button
              onClick={() => setActiveTab("customer")}
              className={`px-4 py-2 rounded-md font-medium transition cursor-pointer ${
                activeTab === "customer" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              Submit Complaint
            </button>
          </div>
        </header>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center justify-between text-slate-400 text-sm">
              <span>Total Tickets</span>
              <Icons.FileText />
            </div>
            <p className="text-2xl font-bold mt-2">{stats.total_tickets}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center justify-between text-slate-400 text-sm">
              <span>Critical Alerts</span>
              <Icons.ShieldAlert />
            </div>
            <p className="text-2xl font-bold mt-2 text-red-400">{stats.critical_tickets}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center justify-between text-slate-400 text-sm">
              <span>Open Queue</span>
              <Icons.Clock />
            </div>
            <p className="text-2xl font-bold mt-2 text-yellow-400">{stats.open_tickets}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center justify-between text-slate-400 text-sm">
              <span>Needs Review</span>
              <Icons.AlertCircle />
            </div>
            <p className="text-2xl font-bold mt-2 text-purple-400">{stats.needs_manual_review}</p>
          </div>
        </div>

        {/* View: Customer Submission */}
        {activeTab === "customer" && (
          <div className="max-w-2xl mx-auto bg-slate-900/40 border border-slate-800 p-6 rounded-2xl shadow-xl">
            <h2 className="text-lg font-semibold mb-4 text-white">Log a Grievance</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    placeholder="e.g. John Doe"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Email Address</label>
                  <input
                    type="email"
                    value={customerEmail}
                    onChange={(e) => setCustomerEmail(e.target.value)}
                    placeholder="e.g. john@example.com"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Complaint Narrative *</label>
                <textarea
                  rows="5"
                  required
                  value={complaintText}
                  onChange={(e) => setComplaintText(e.target.value)}
                  placeholder="Describe your issue with reference numbers, amounts, or incident details..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm focus:outline-none focus:border-indigo-500"
                ></textarea>
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 font-medium rounded-lg text-sm flex items-center justify-center gap-2 transition disabled:opacity-50 cursor-pointer"
              >
                <Icons.Send />
                {submitting ? "Analyzing & Classifying..." : "Submit Grievance to AI Engine"}
              </button>
            </form>
          </div>
        )}

        {/* View: Agent Queue */}
        {activeTab === "agent" && (
          <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/80">
              <h2 className="text-base font-semibold">Live Automated Triage Queue</h2>
              <button
                onClick={fetchData}
                className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition text-slate-300 cursor-pointer"
              >
                <Icons.Refresh /> Refresh Queue
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-950/60 text-slate-400 uppercase text-[11px] tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Ticket</th>
                    <th className="py-3 px-4">Narrative</th>
                    <th className="py-3 px-4">AI Category</th>
                    <th className="py-3 px-4">Urgency</th>
                    <th className="py-3 px-4">Entities</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {complaints.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="text-center py-8 text-slate-500">
                        No active complaints found. Use the "Submit Complaint" tab to log a ticket!
                      </td>
                    </tr>
                  ) : (
                    complaints.map((c) => {
                      const entities = parseEntities(c.extracted_entities);
                      return (
                        <tr key={c.id} className="hover:bg-slate-900/30 transition">
                          <td className="py-4 px-4 font-mono text-xs text-indigo-400">
                            #{c.id}
                          </td>
                          <td className="py-4 px-4 max-w-sm">
                            <p className="font-medium text-slate-200 line-clamp-2">{c.text}</p>
                            <span className="text-xs text-slate-500">From: {c.customer_name}</span>
                          </td>
                          <td className="py-4 px-4">
                            <div className="font-medium text-slate-300">{c.category}</div>
                            <div className="text-[11px] text-slate-500">{c.category_confidence}% match</div>
                          </td>
                          <td className="py-4 px-4">
                            {getUrgencyBadge(c.urgency)}
                          </td>
                          <td className="py-4 px-4 text-xs font-mono text-slate-400">
                            {entities.reference_id && <div>Ref: {entities.reference_id}</div>}
                            {entities.amount && <div>Amt: {entities.amount}</div>}
                            {!entities.reference_id && !entities.amount && <span className="text-slate-600">—</span>}
                          </td>
                          <td className="py-4 px-4">
                            <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                              c.status === "Resolved" ? "bg-emerald-500/20 text-emerald-400" : "bg-blue-500/20 text-blue-400"
                            }`}>
                              {c.status}
                            </span>
                          </td>
                          <td className="py-4 px-4">
                            {c.status !== "Resolved" ? (
                              <button
                                onClick={() => updateStatus(c.id, "Resolved")}
                                className="px-2.5 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-400 text-xs rounded-md transition font-medium flex items-center gap-1 cursor-pointer"
                              >
                                <Icons.CheckCircle /> Resolve
                              </button>
                            ) : (
                              <span className="text-xs text-slate-500">Closed</span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}