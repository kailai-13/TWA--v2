import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { studentAPI } from '../utils/api'
import { startCamera, stopCamera, captureImage } from '../utils/camera'
import '../styles/Dashboard.css'
import '../styles/Camera.css'

const StudentDashboard = () => {
  const [studentData, setStudentData] = useState(null)
  const [activeRooms, setActiveRooms] = useState([])
  const [attendanceHistory, setAttendanceHistory] = useState([])
  const [selectedRoom, setSelectedRoom] = useState('')
  const [step, setStep] = useState('select') // select, capture, verify
  const [cameraActive, setCameraActive] = useState(false)
  const [stream, setStream] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('')
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    const student = JSON.parse(localStorage.getItem('studentData'))
    if (!student) {
      navigate('/student/login')
      return
    }
    setStudentData(student)
    fetchActiveRooms()
    fetchAttendanceHistory(student.roll_number)

    // Start activity monitoring
    const activityInterval = setInterval(() => {
      updateActivity(student.roll_number)
    }, 30000) // Every 30 seconds

    return () => {
      clearInterval(activityInterval)
      if (stream) {
        stopCamera(stream)
      }
    }
  }, [navigate])

  const fetchActiveRooms = async () => {
    try {
      const response = await studentAPI.getActiveRooms()
      if (response.data.success) {
        setActiveRooms(response.data.rooms)
      }
    } catch (error) {
      console.error('Error fetching active rooms:', error)
    }
  }

  const fetchAttendanceHistory = async (rollNumber) => {
    try {
      const response = await studentAPI.getAttendanceHistory(rollNumber)
      if (response.data.success) {
        setAttendanceHistory(response.data.attendance)
      }
    } catch (error) {
      console.error('Error fetching attendance history:', error)
    }
  }

  const updateActivity = async (rollNumber) => {
    try {
      await studentAPI.updateActivity({ roll_number: rollNumber })
    } catch (error) {
      console.error('Error updating activity:', error)
    }
  }

  const handleRoomSelect = (roomCode) => {
    setSelectedRoom(roomCode)
    setMessage('')
    setStep('capture')
  }

  const handleStartCamera = async () => {
    try {
      const cameraStream = await startCamera(videoRef)
      setStream(cameraStream)
      setCameraActive(true)
      setMessage('')
    } catch (error) {
      setMessage('Failed to access camera. Please check permissions.')
      setMessageType('error')
    }
  }

  const handleMarkAttendance = async () => {
    setLoading(true)
    setMessage('')

    try {
      // First check eligibility
      const eligibilityResponse = await studentAPI.checkEligibility({
        roll_number: studentData.roll_number,
        room_code: selectedRoom
      })

      if (!eligibilityResponse.data.success) {
        setMessage(eligibilityResponse.data.message)
        setMessageType('error')
        setLoading(false)
        return
      }

      // Capture and verify face
      const imageData = captureImage(videoRef, canvasRef)
      if (!imageData) {
        setMessage('Failed to capture image')
        setMessageType('error')
        setLoading(false)
        return
      }

      const verifyResponse = await studentAPI.verifyFace({
        roll_number: studentData.roll_number,
        room_code: selectedRoom,
        face_image: imageData
      })

      if (verifyResponse.data.success) {
        setMessage('Attendance marked successfully!')
        setMessageType('success')
        setStep('success')
        fetchAttendanceHistory(studentData.roll_number)
        
        // Update student data
        const updatedStudent = { ...studentData, current_room: selectedRoom }
        setStudentData(updatedStudent)
        localStorage.setItem('studentData', JSON.stringify(updatedStudent))
      } else {
        setMessage(verifyResponse.data.message)
        setMessageType('error')
      }
    } catch (error) {
      setMessage(error.response?.data?.message || 'Attendance marking failed')
      setMessageType('error')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    try {
      await studentAPI.logout({ roll_number: studentData.roll_number })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('studentData')
      navigate('/')
    }
  }

  const resetProcess = () => {
    setStep('select')
    setSelectedRoom('')
    setMessage('')
    if (stream) {
      stopCamera(stream)
      setStream(null)
    }
    setCameraActive(false)
  }

  if (!studentData) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-left">
          <h1>Student Dashboard</h1>
          <p>Welcome, {studentData.username}</p>
        </div>
        <div className="header-right">
          <span className="student-info">
            Roll: {studentData.roll_number}
            {studentData.current_room && (
              <span className="current-room">Room: {studentData.current_room}</span>
            )}
          </span>
          <button onClick={handleLogout} className="btn btn-secondary">Logout</button>
        </div>
      </header>

      <div className="dashboard-content">
        <div className="attendance-section">
          <h2>Mark Attendance</h2>
          
          {step === 'select' && (
            <div className="room-selection">
              <h3>Select a Room</h3>
              {activeRooms.length === 0 ? (
                <p>No active rooms available</p>
              ) : (
                <div className="rooms-list">
                  {activeRooms.map((room) => (
                    <div key={room.room_code} className="room-option">
                      <h4>{room.room_code}</h4>
                      <p>Admin: {room.admin_name}</p>
                      <p>Members: {room.member_count}</p>
                      <p>Created: {room.created_at}</p>
                      <button 
                        onClick={() => handleRoomSelect(room.room_code)}
                        className="btn btn-primary"
                      >
                        Join Room
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {step === 'capture' && (
            <div className="face-verification">
              <h3>Face Verification for {selectedRoom}</h3>
              <p>Please position your face in the camera and click "Mark Attendance"</p>
              
              {!cameraActive ? (
                <button onClick={handleStartCamera} className="btn btn-secondary">
                  Start Camera
                </button>
              ) : (
                <div className="camera-container">
                  <video ref={videoRef} autoPlay playsInline className="camera-video" />
                  <canvas ref={canvasRef} style={{ display: 'none' }} />
                  <div className="camera-controls">
                    <button 
                      onClick={handleMarkAttendance} 
                      className="btn btn-primary"
                      disabled={loading}
                    >
                      {loading ? 'Verifying...' : 'Mark Attendance'}
                    </button>
                    <button onClick={resetProcess} className="btn btn-secondary">
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 'success' && (
            <div className="success-state">
              <h3>✅ Attendance Marked!</h3>
              <p>Your attendance has been successfully recorded for room {selectedRoom}</p>
              <button onClick={resetProcess} className="btn btn-primary">
                Mark Another Room
              </button>
            </div>
          )}

          {message && (
            <div className={`message ${messageType}`}>
              {message}
            </div>
          )}
        </div>

        <div className="history-section">
          <h2>Attendance History</h2>
          {attendanceHistory.length === 0 ? (
            <p>No attendance records found</p>
          ) : (
            <div className="history-table">
              <table>
                <thead>
                  <tr>
                    <th>Room Code</th>
                    <th>Login Time</th>
                    <th>Logout Time</th>
                    <th>Duration</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {attendanceHistory.map((record, index) => (
                    <tr key={index}>
                      <td>{record.room_code}</td>
                      <td>{record.login_time}</td>
                      <td>{record.logout_time || 'Still Active'}</td>
                      <td>{record.duration}</td>
                      <td>
                        <span className={`status ${record.status.toLowerCase()}`}>
                          {record.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default StudentDashboard
