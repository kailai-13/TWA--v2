import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { studentAPI } from '../utils/api'
import '../styles/Auth.css'

const StudentLogin = () => {
  const [formData, setFormData] = useState({
    roll_number: '',
    password: ''
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('')
  const navigate = useNavigate()

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      const response = await studentAPI.login(formData)

      if (response.data.success) {
        localStorage.setItem('studentData', JSON.stringify(response.data.student))
        setMessage('Login successful! Redirecting...')
        setMessageType('success')
        setTimeout(() => {
          navigate('/student/dashboard')
        }, 1500)
      } else {
        setMessage(response.data.message)
        setMessageType('error')
      }
    } catch (error) {
      setMessage(error.response?.data?.message || 'Login failed')
      setMessageType('error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2>Student Login</h2>
          <p>Sign in to mark your attendance</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
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

          {message && (
            <div className={`message ${messageType}`}>
              {message}
            </div>
          )}

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="auth-footer">
          <p>Don't have an account? <Link to="/student/register">Register here</Link></p>
          <Link to="/" className="back-home">← Back to Home</Link>
        </div>
      </div>
    </div>
  )
}

export default StudentLogin
