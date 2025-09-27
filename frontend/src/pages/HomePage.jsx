import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../utils/api'
import '../styles/HomePage.css'

const HomePage = () => {
  const [bssid, setBssid] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchBssid = async () => {
      try {
        const response = await api.get('/health')
        setBssid(response.data.bssid)
      } catch (error) {
        console.error('Error fetching BSSID:', error)
        setBssid('Connection Error')
      } finally {
        setLoading(false)
      }
    }

    fetchBssid()
  }, [])

  return (
    <div className="home-container">
      <div className="home-content">
        <header className="home-header">
          <h1 className="home-title">Smart Attendance System</h1>
          <p className="home-subtitle">Face Recognition & WiFi-based Attendance Management</p>
        </header>

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">👥</div>
            <h3>Real-time Tracking</h3>
            <p>Monitor student attendance in real-time with live updates</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔐</div>
            <h3>Face Recognition</h3>
            <p>Secure authentication using advanced face recognition technology</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📱</div>
            <h3>Multi-device Support</h3>
            <p>Access from any device with a modern web browser</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Analytics & Reports</h3>
            <p>Comprehensive attendance reports and analytics</p>
          </div>
        </div>

        <div className="user-type-selection">
          <h2>Choose Your Role</h2>
          <div className="role-cards">
            <div className="role-card admin-card">
              <h3>Administrator</h3>
              <p>Create and manage attendance rooms, monitor students</p>
              <div className="role-buttons">
                <Link to="/admin/login" className="btn btn-primary">Login</Link>
                <Link to="/admin/register" className="btn btn-secondary">Register</Link>
              </div>
            </div>
            <div className="role-card student-card">
              <h3>Student</h3>
              <p>Join attendance rooms and track your attendance</p>
              <div className="role-buttons">
                <Link to="/student/login" className="btn btn-primary">Login</Link>
                <Link to="/student/register" className="btn btn-secondary">Register</Link>
              </div>
            </div>
          </div>
        </div>

        {!loading && (
          <div className="network-info">
            <div className="network-card">
              <h4>Current Network</h4>
              <p className="bssid-info">BSSID: {bssid}</p>
              <small>Make sure you're connected to the correct WiFi network</small>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default HomePage
