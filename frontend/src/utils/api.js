import axios from 'axios'

const API_BASE_URL = 'http://localhost:5000/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// Admin API calls
export const adminAPI = {
  register: (data) => api.post('/admin/register', data),
  login: (data) => api.post('/admin/login', data),
  logout: (adminId) => api.post(`/admin/logout/${adminId}`),
  getRooms: (adminId) => api.get(`/admin/${adminId}/rooms`),
  createRoom: (data) => api.post('/admin/rooms', data),
  getRoomMembers: (roomCode) => api.get(`/admin/rooms/${roomCode}/members`),
  addMember: (data) => api.post(`/admin/rooms/${data.room_code}/members`, data),
  updateMemberStatus: (data) => api.post('/admin/members/status', data),
  closeRoom: (roomCode) => api.post(`/admin/rooms/${roomCode}/close`),
  downloadAttendance: (roomCode) => api.get(`/admin/rooms/${roomCode}/attendance/download`, {
    responseType: 'blob'
  }),
  getStats: (adminId) => api.get(`/admin/stats/${adminId}`)
}

// Student API calls
export const studentAPI = {
  register: (data) => api.post('/student/register', data),
  login: (data) => api.post('/student/login', data),
  checkEligibility: (data) => api.post('/student/eligibility', data),
  verifyFace: (data) => api.post('/student/face/verify', data),
  getActiveRooms: () => api.get('/student/rooms/active'),
  updateActivity: (data) => api.post('/student/activity', data),
  logout: (data) => api.post('/student/logout', data),
  getAttendanceHistory: (rollNumber) => api.get(`/student/${rollNumber}/attendance`)
}

// Face recognition API calls
export const faceAPI = {
  registerFace: (data) => api.post('/face/register', data),
  verifyFace: (data) => api.post('/face/verify', data)
}
