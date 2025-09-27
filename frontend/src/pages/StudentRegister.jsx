import React, { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { studentAPI } from '../utils/api'
import { startCamera, stopCamera, captureImage } from '../utils/camera'
import '../styles/Auth.css'
import '../styles/Camera.css'

const StudentRegister = () => {
  const [formData, setFormData] = useState({
    roll_number: '',
    username: '',
    password: '',
    confirmPassword: ''
  })
  const [cameraActive, setCameraActive] = useState(false)
  const [capturedImage, setCapturedImage] = useState('')
  const [stream, setStream] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('')
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    return () => {
      if (stream) {
        stopCamera(stream)
      }
    }
  }, [stream])

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
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

  const handleCaptureImage = () => {
    const imageData = captureImage(videoRef, canvasRef)
    if (imageData) {
      setCapturedImage(imageData)
      setMessage('Face captured successfully!')
      setMessageType('success')
    } else {
      setMessage('Failed to capture image')
      setMessageType('error')
    }
  }

  const handleRetakePhoto = () => {
    setCapturedImage('')
    setMessage('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    if (formData.password !== formData.confirmPassword) {
      setMessage('Passwords do not match')
      setMessageType('error')
      setLoading(false)
      return
    }

    if (formData.password.length < 6) {
      setMessage('Password must be at least 6 characters long')
      setMessageType('error')
      setLoading(false)
      return
    }

    if (!capturedImage) {
      setMessage('Please capture your face image')
      setMessageType('error')
      setLoading(false)
      return
    }

    try {
      const response = await studentAPI.register({
        roll_number: formData.roll_number,
        username: formData.username,
        password: formData.password,
        face_image: capturedImage
      })

      if (response.data.success) {
        setMessage('Registration successful! Redirecting to login...')
        setMessageType('success')
        setTimeout(() => {
          navigate('/student/login')
        }, 2000)
      } else {
        setMessage(response.data.message)
        setMessageType('error')
      }
    } catch (error) {
      setMessage(error.response?.data?.message || 'Registration failed')
      setMessageType('error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card large">
        <div className="auth-header">
          <h2>Student Registration</h2>
          <p>Create your student account with face registration</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="roll_number">Roll Number</label>
              <input
                type="text"
                id="roll_number"
                name="roll_number"
                value={formData.roll_number}
                onChange={handleInputChange}
                required
                placeholder="Enter your roll number"
              />
            </div>

            <div className="form-group">
              <label htmlFor="username">Full Name</label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                required
                placeholder="Enter your full name"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                placeholder="Enter your password"
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                required
                placeholder="Confirm your password"
              />
            </div>
          </div>

          <div className="camera-section">
            <h3>Face Registration</h3>
            <p>Please capture a clear photo of your face for attendance verification</p>
            
            {!cameraActive ? (
              <button 
                type="button" 
                onClick={handleStartCamera} 
                className="btn btn-secondary"
              >
                Start Camera
              </button>
            ) : (
              <div className="camera-container">
                {!capturedImage ? (
                  <div className="video-container">
                    <video ref={videoRef} autoPlay playsInline className="camera-video" />
                    <canvas ref={canvasRef} style={{ display: 'none' }} />
                    <div className="camera-controls">
                      <button 
                        type="button" 
                        onClick={handleCaptureImage} 
                        className="btn btn-primary"
                      >
                        Capture Photo
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="captured-image-container">
                    <img src={capturedImage} alt="Captured face" className="captured-image" />
                    <div className="camera-controls">
                      <button 
                        type="button" 
                        onClick={handleRetakePhoto} 
                        className="btn btn-secondary"
                      >
                        Retake Photo
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {message && (
            <div className={`message ${messageType}`}>
              {message}
            </div>
          )}

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Registering...' : 'Register'}
          </button>
        </form>

        <div className="auth-footer">
          <p>Already have an account? <Link to="/student/login">Login here</Link></p>
          <Link to="/" className="back-home">← Back to Home</Link>
        </div>
      </div>
    </div>
  )
}

export default StudentRegister
