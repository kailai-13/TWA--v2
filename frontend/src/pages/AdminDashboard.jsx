import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { adminAPI } from '../utils/api'
import '../styles/Dashboard.css'

const AdminDashboard = () => {
  const [adminData, setAdminData] = useState(null)
  const [rooms, setRooms] = useState([])
  const [stats, setStats] = useState({})
  const [newRoomCode, setNewRoomCode] = useState('')
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const admin = JSON.parse(localStorage.getItem('adminData'))
    if (!admin) {
      navigate('/admin/login')
      return
    }
    setAdminData(admin)
    fetchRooms(admin.id)
    fetchStats(admin.id)
  }, [navigate])

  const fetchRooms = async (adminId) => {
    try {
      const response = await adminAPI.getRooms(adminId)
      if (response.data.success) {
        setRooms(response.data.rooms)
      }
    } catch (error) {
      console.error('Error fetching rooms:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async (adminId) => {
    try {
      const response = await adminAPI.getStats(adminId)
      if (response.data.success) {
        setStats(response.data.stats)
      }
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  const handleCreateRoom = async (e) => {
    e.preventDefault()
    if (!newRoomCode.trim()) return

    try {
      const response = await adminAPI.createRoom({
        room_code: newRoomCode,
        admin_id: adminData.id
      })

      if (response.data.success) {
        setMessage(response.data.message)
        setMessageType('success')
        setNewRoomCode('')
        fetchRooms(adminData.id)
        fetchStats(adminData.id)
      } else {
        setMessage(response.data.message)
        setMessageType('error')
      }
    } catch (error) {
      setMessage(error.response?.data?.message || 'Failed to create room')
      setMessageType('error')
    }
  }

  const handleLogout = async () => {
    try {
      await adminAPI.logout(adminData.id)
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('adminData')
      navigate('/')
    }
  }

  const getRoomStatusColor = (status) => {
    switch (status) {
      case 'Active': return '#28a745'
      case 'Temporarily Closed': return '#ffc107'
      case 'Inactive': return '#dc3545'
      default: return '#6c757d'
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-left">
          <h1>Admin Dashboard</h1>
          <p>Welcome back, {adminData?.username}</p>
        </div>
        <div className="header-right">
          <span className="admin-info">ID: {adminData?.idname}</span>
          <button onClick={handleLogout} className="btn btn-secondary">Logout</button>
        </div>
      </header>

      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-icon">🏢</div>
          <div className="stat-content">
            <h3>{stats.total_rooms || 0}</h3>
            <p>Total Rooms</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <h3>{stats.active_rooms || 0}</h3>
            <p>Active Rooms</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <h3>{stats.total_members || 0}</h3>
            <p>Total Students</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">👋</div>
          <div className="stat-content">
            <h3>{stats.present_members || 0}</h3>
            <p>Present Now</p>
          </div>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="create-room-section">
          <h2>Create New Room</h2>
          <form onSubmit={handleCreateRoom} className="create-room-form">
            <div className="form-group">
              <input
                type="text"
                value={newRoomCode}
                onChange={(e) => setNewRoomCode(e.target.value)}
                placeholder="Enter room code"
                required
              />
              <button type="submit" className="btn btn-primary">Create Room</button>
            </div>
          </form>
          {message && (
            <div className={`message ${messageType}`}>
              {message}
            </div>
          )}
        </div>

        <div className="rooms-section">
          <h2>Your Rooms</h2>
          {rooms.length === 0 ? (
            <div className="empty-state">
              <p>No rooms created yet. Create your first room above!</p>
            </div>
          ) : (
            <div className="rooms-grid">
              {rooms.map((room) => (
                <div key={room.id} className="room-card">
                  <div className="room-header">
                    <h3>{room.room_code}</h3>
                    <span 
                      className="room-status"
                      style={{ backgroundColor: getRoomStatusColor(room.status) }}
                    >
                      {room.status}
                    </span>
                  </div>
                  <div className="room-info">
                    <p><strong>Created:</strong> {room.created_at}</p>
                    <p><strong>Members:</strong> {room.member_count}</p>
                    <p><strong>Present:</strong> {room.present_count}</p>
                    <p><strong>BSSID:</strong> {room.bssid?.substring(0, 17)}...</p>
                  </div>
                  <div className="room-actions">
                    <Link 
                      to={`/admin/room/${room.room_code}`} 
                      className="btn btn-primary btn-sm"
                    >
                      Manage
                    </Link>
                    <Link 
                      to={`/admin/attendance/${room.room_code}`} 
                      className="btn btn-secondary btn-sm"
                    >
                      Reports
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AdminDashboard
