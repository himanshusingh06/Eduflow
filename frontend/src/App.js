import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import toast, { Toaster } from 'react-hot-toast';
import { User, BookOpen, GraduationCap, MessageSquare, BarChart3, Settings, LogOut, Brain, Users, PenTool, Menu, X } from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Set default axios headers
axios.defaults.baseURL = API;

// Auth Context
const AuthContext = createContext();
const useAuth = () => useContext(AuthContext);

// Auth Provider Component
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get('/auth/me');
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch current user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = (userData, userToken) => {
    setUser(userData);
    setToken(userToken);
    localStorage.setItem('token', userToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${userToken}`;
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Login Component
const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    role: 'student'
  });
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const response = await axios.post(endpoint, formData);
      
      login(response.data.user, response.data.access_token);
      toast.success(isLogin ? 'Logged in successfully!' : 'Account created successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md backdrop-blur-sm bg-opacity-95">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Brain className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">EduAgent</h1>
          <p className="text-gray-600">AI-Powered Learning Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <>
              <input
                type="text"
                placeholder="Full Name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                required={!isLogin}
                data-testid="register-name-input"
              />
              <select
                value={formData.role}
                onChange={(e) => setFormData({...formData, role: e.target.value})}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                data-testid="register-role-select"
              >
                <option value="student">Student</option>
                <option value="teacher">Teacher</option>
                <option value="parent">Parent</option>
              </select>
            </>
          )}
          
          <input
            type="email"
            placeholder="Email"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
            required
            data-testid="login-email-input"
          />
          
          <input
            type="password"
            placeholder="Password"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
            required
            data-testid="login-password-input"
          />
          
          <button
            type="submit"
            className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 text-white py-3 rounded-xl font-semibold hover:from-emerald-600 hover:to-teal-700 transform hover:scale-[1.02] transition-all duration-200 shadow-lg"
            data-testid="login-submit-button"
          >
            {isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="text-center mt-6">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-emerald-600 hover:text-emerald-700 font-medium transition-colors"
            data-testid="auth-toggle-button"
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
};

// Sidebar Component
const Sidebar = ({ activeTab, setActiveTab, user, isMobileOpen, setIsMobileOpen }) => {
  const { logout } = useAuth();
  
  const getMenuItems = (role) => {
    const commonItems = [
      { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
      { id: 'chat', label: 'Messages', icon: MessageSquare },
    ];
    
    if (role === 'student') {
      return [
        ...commonItems,
        { id: 'study', label: 'Study Content', icon: BookOpen },
        { id: 'quiz', label: 'Quizzes', icon: PenTool },
        { id: 'ask', label: 'Ask AI', icon: Brain },
        { id: 'notes', label: 'My Notes', icon: BookOpen },
        { id: 'learning-path', label: 'Learning Path', icon: Brain },
        { id: 'subscription', label: 'Subscription', icon: GraduationCap },
      ];
    }
    
    if (role === 'teacher') {
      return [
        ...commonItems,
        { id: 'create-content', label: 'Create Content', icon: BookOpen },
        { id: 'create-quiz', label: 'Create Quiz', icon: PenTool },
        { id: 'students', label: 'Students', icon: Users },
      ];
    }
    
    if (role === 'parent') {
      return [
        ...commonItems,
        { id: 'children', label: 'My Children', icon: Users },
        { id: 'progress', label: 'Progress Reports', icon: BarChart3 },
      ];
    }
    
    return commonItems;
  };

  const menuItems = getMenuItems(user?.role);

  return (
    <>
      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      <div className={`
        fixed left-0 top-0 h-full bg-white shadow-xl z-50 w-64 transform transition-transform duration-300
        lg:relative lg:translate-x-0 lg:z-0
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="p-6 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="font-bold text-lg">EduAgent</h2>
                <p className="text-sm text-gray-600 capitalize">{user?.role}</p>
              </div>
            </div>
            <button 
              onClick={() => setIsMobileOpen(false)}
              className="lg:hidden p-2 hover:bg-gray-100 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {menuItems.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.id}>
                  <button
                    onClick={() => {
                      setActiveTab(item.id);
                      setIsMobileOpen(false);
                    }}
                    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-left transition-all ${
                      activeTab === item.id
                        ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg'
                        : 'text-gray-600 hover:bg-emerald-50 hover:text-emerald-700'
                    }`}
                    data-testid={`sidebar-${item.id}`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
        
        <div className="p-4 border-t">
          <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-xl mb-3">
            <User className="w-8 h-8 text-gray-600" />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{user?.name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          
          <button
            onClick={logout}
            className="w-full flex items-center space-x-3 px-4 py-3 text-red-600 hover:bg-red-50 rounded-xl transition-all"
            data-testid="logout-button"
          >
            <LogOut className="w-5 h-5" />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </div>
    </>
  );
};

// Dashboard Components for each role
const StudentDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get('/dashboard/student');
      setDashboardData(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6">Loading dashboard...</div>;
  }

  return (
    <div className="p-6 space-y-6" data-testid="student-dashboard">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome back, {dashboardData?.user?.name}!</h1>
        <p className="text-gray-600">Continue your learning journey with AI-powered assistance</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Quizzes Completed</p>
              <p className="text-3xl font-bold">{dashboardData?.quick_stats?.total_quizzes_taken || 0}</p>
            </div>
            <PenTool className="w-8 h-8 text-blue-200" />
          </div>
        </div>
        
        <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-emerald-100 text-sm">Questions Asked</p>
              <p className="text-3xl font-bold">{dashboardData?.quick_stats?.questions_asked || 0}</p>
            </div>
            <Brain className="w-8 h-8 text-emerald-200" />
          </div>
        </div>
        
        <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Study Materials</p>
              <p className="text-3xl font-bold">{dashboardData?.available_content?.length || 0}</p>
            </div>
            <BookOpen className="w-8 h-8 text-purple-200" />
          </div>
        </div>
      </div>

      {/* Recent Activities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Quiz Results</h3>
          {dashboardData?.recent_quiz_attempts?.length ? (
            <div className="space-y-3">
              {dashboardData.recent_quiz_attempts.slice(0, 5).map((attempt, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">Quiz #{attempt.quiz_id.slice(-6)}</p>
                    <p className="text-sm text-gray-600">Completed: {new Date(attempt.completed_at).toLocaleDateString()}</p>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                    attempt.percentage >= 80 ? 'bg-green-100 text-green-800' :
                    attempt.percentage >= 60 ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {Math.round(attempt.percentage)}%
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No quizzes taken yet. Start with your first quiz!</p>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">Available Quizzes</h3>
          {dashboardData?.available_quizzes?.length ? (
            <div className="space-y-3">
              {dashboardData.available_quizzes.slice(0, 5).map((quiz, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                  <div>
                    <p className="font-medium">{quiz.title}</p>
                    <p className="text-sm text-gray-600">{quiz.subject} • {quiz.questions.length} questions</p>
                  </div>
                  <button className="px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm hover:bg-emerald-600 transition-colors">
                    Take Quiz
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No quizzes available yet.</p>
          )}
        </div>
      </div>
    </div>
  );
};

const TeacherDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get('/dashboard/teacher');
      setDashboardData(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6">Loading dashboard...</div>;
  }

  return (
    <div className="p-6 space-y-6" data-testid="teacher-dashboard">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Teacher Dashboard</h1>
        <p className="text-gray-600">Manage your content and track student progress</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-indigo-100 text-sm">Content Created</p>
              <p className="text-3xl font-bold">{dashboardData?.stats?.total_content_created || 0}</p>
            </div>
            <BookOpen className="w-8 h-8 text-indigo-200" />
          </div>
        </div>
        
        <div className="bg-gradient-to-r from-green-500 to-green-600 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100 text-sm">Quizzes Created</p>
              <p className="text-3xl font-bold">{dashboardData?.stats?.total_quizzes_created || 0}</p>
            </div>
            <PenTool className="w-8 h-8 text-green-200" />
          </div>
        </div>
        
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-orange-100 text-sm">Student Attempts</p>
              <p className="text-3xl font-bold">{dashboardData?.stats?.total_student_attempts || 0}</p>
            </div>
            <Users className="w-8 h-8 text-orange-200" />
          </div>
        </div>
      </div>

      {/* Content Management */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">My Content</h3>
          {dashboardData?.my_content?.length ? (
            <div className="space-y-3">
              {dashboardData.my_content.slice(0, 5).map((content, idx) => (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                  <p className="font-medium">{content.title}</p>
                  <p className="text-sm text-gray-600">{content.subject} • {content.grade_level}</p>
                  <p className="text-xs text-gray-500">Created: {new Date(content.created_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No content created yet. Start creating study materials!</p>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border p-6">
          <h3 className="text-lg font-semibold mb-4">My Quizzes</h3>
          {dashboardData?.my_quizzes?.length ? (
            <div className="space-y-3">
              {dashboardData.my_quizzes.slice(0, 5).map((quiz, idx) => (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                  <p className="font-medium">{quiz.title}</p>
                  <p className="text-sm text-gray-600">{quiz.subject} • {quiz.questions.length} questions</p>
                  <p className="text-xs text-gray-500">Created: {new Date(quiz.created_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No quizzes created yet. Create your first quiz!</p>
          )}
        </div>
      </div>
    </div>
  );
};

const ParentDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get('/dashboard/parent');
      setDashboardData(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6">Loading dashboard...</div>;
  }

  return (
    <div className="p-6 space-y-6" data-testid="parent-dashboard">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Parent Dashboard</h1>
        <p className="text-gray-600">Monitor your children's learning progress</p>
      </div>

      {/* Children Overview */}
      <div className="bg-white rounded-2xl shadow-sm border p-6">
        <h3 className="text-lg font-semibold mb-4">My Children</h3>
        {dashboardData?.students?.length ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {dashboardData.students.map((student, idx) => (
              <div key={idx} className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center">
                    <User className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <p className="font-medium">{student.name}</p>
                    <p className="text-sm text-gray-600">{student.email}</p>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-blue-200">
                  <button className="text-blue-600 text-sm font-medium hover:text-blue-700">
                    View Progress →
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No children linked to your account yet.</p>
        )}
      </div>

      {/* Progress Summary */}
      <div className="bg-white rounded-2xl shadow-sm border p-6">
        <h3 className="text-lg font-semibold mb-4">Progress Summary</h3>
        {dashboardData?.student_progress?.length ? (
          <div className="space-y-4">
            {dashboardData.student_progress.map((item, idx) => (
              <div key={idx} className="p-4 bg-gray-50 rounded-xl">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <p className="font-medium">{item.student.name}</p>
                    <p className="text-sm text-gray-600">Overall Progress</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-emerald-600">{item.progress.average_score}%</p>
                    <p className="text-xs text-gray-500">{item.progress.total_quizzes} quizzes</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Questions Asked</p>
                    <p className="font-medium">{item.progress.total_questions_asked}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Subjects</p>
                    <p className="font-medium">{Object.keys(item.progress.subject_breakdown || {}).length}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No progress data available yet.</p>
        )}
      </div>
    </div>
  );
};

// Study Content Component
const StudyContent = () => {
  const [content, setContent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ subject: '', grade_level: '' });

  useEffect(() => {
    fetchContent();
  }, [filters]);

  const fetchContent = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.subject) params.append('subject', filters.subject);
      if (filters.grade_level) params.append('grade_level', filters.grade_level);
      
      const response = await axios.get(`/study/content?${params}`);
      setContent(response.data);
    } catch (error) {
      toast.error('Failed to load content');
    } finally {
      setLoading(false);
    }
  };

  const purchaseCourse = async (courseItem) => {
    try {
      // Create payment order
      const response = await axios.post('/create-order', {
        amount: 50000, // Rs 500 for a course
        description: `Purchase: ${courseItem.title}`,
        payment_type: 'one_time'
      });

      if (response.data.success) {
        const options = {
          key: response.data.key_id,
          amount: response.data.amount,
          currency: response.data.currency,
          name: 'EduAgent - Learning Platform',
          description: `Course: ${courseItem.title}`,
          order_id: response.data.order_id,
          handler: async function (razorpayResponse) {
            try {
              await axios.post('/verify-payment', {
                order_id: razorpayResponse.razorpay_order_id,
                payment_id: razorpayResponse.razorpay_payment_id,
                signature: razorpayResponse.razorpay_signature
              });
              
              toast.success('Course purchased successfully!');
            } catch (error) {
              toast.error('Payment verification failed');
            }
          },
          prefill: {
            name: 'Student Name',
            email: 'student@example.com',
            contact: '9999999999'
          },
          theme: {
            color: '#10b981'
          }
        };

        const rzp = new window.Razorpay(options);
        rzp.open();
      }
    } catch (error) {
      toast.error('Failed to create payment order');
    }
  };

  if (loading) return <div className="p-6">Loading content...</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Study Content</h1>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl p-4 shadow-sm border">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <select
            value={filters.subject}
            onChange={(e) => setFilters({...filters, subject: e.target.value})}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">All Subjects</option>
            <option value="Mathematics">Mathematics</option>
            <option value="Science">Science</option>
            <option value="English">English</option>
            <option value="History">History</option>
          </select>
          <select
            value={filters.grade_level}
            onChange={(e) => setFilters({...filters, grade_level: e.target.value})}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">All Grades</option>
            <option value="Grade 6">Grade 6</option>
            <option value="Grade 7">Grade 7</option>
            <option value="Grade 8">Grade 8</option>
            <option value="Grade 9">Grade 9</option>
            <option value="Grade 10">Grade 10</option>
          </select>
        </div>
      </div>

      {/* Content List */}
      <div className="grid grid-cols-1 gap-6">
        {content.length > 0 ? (
          content.map((item, idx) => (
            <div key={idx} className="bg-white rounded-xl p-6 shadow-sm border">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">{item.title}</h3>
                  <p className="text-gray-600">{item.subject} • {item.grade_level}</p>
                </div>
                <div className="text-xs text-gray-500">
                  {new Date(item.created_at).toLocaleDateString()}
                </div>
              </div>
              <div className="prose max-w-none text-gray-700">
                {item.content.substring(0, 300)}...
              </div>
              <div className="flex items-center justify-between mt-4">
                <div className="flex flex-wrap gap-2">
                  {item.tags.map((tag, tagIdx) => (
                    <span key={tagIdx} className="px-2 py-1 bg-emerald-100 text-emerald-800 text-xs rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="flex space-x-2">
                  <button 
                    onClick={() => purchaseCourse(item)}
                    className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors"
                  >
                    Purchase ₹500
                  </button>
                  <button className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors">
                    Preview
                  </button>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-12">
            <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 text-lg">No study content available</p>
            <p className="text-gray-400">Check back later for new content</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Quiz System Component
const QuizSystem = () => {
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedQuiz, setSelectedQuiz] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [quizResult, setQuizResult] = useState(null);
  const [quizAnalysis, setQuizAnalysis] = useState(null);

  useEffect(() => {
    fetchQuizzes();
  }, []);

  const fetchQuizzes = async () => {
    try {
      const response = await axios.get('/api/quiz/list');
      setQuizzes(response.data || []);
    } catch (error) {
      console.error('Quiz fetch error:', error);
      toast.error('Failed to load quizzes');
      setQuizzes([]); // Set empty array as fallback
    } finally {
      setLoading(false);
    }
  };

  const startQuiz = (quiz) => {
    setSelectedQuiz(quiz);
    setCurrentQuestion(0);
    setAnswers({});
    setQuizResult(null);
    setQuizAnalysis(null);
  };

  const selectAnswer = (questionIndex, optionIndex) => {
    setAnswers({...answers, [questionIndex]: optionIndex});
  };

  const nextQuestion = () => {
    if (currentQuestion < selectedQuiz.questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    }
  };

  const previousQuestion = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    }
  };

  const submitQuiz = async () => {
    try {
      const response = await axios.post(`/api/quiz/${selectedQuiz.id}/attempt`, answers);
      setQuizResult(response.data);
      
      // Fetch quiz analysis
      try {
        const analysisResponse = await axios.get(`/api/quiz/analysis/${response.data.id}`);
        setQuizAnalysis(analysisResponse.data);
      } catch (analysisError) {
        console.error('Analysis fetch error:', analysisError);
      }
      
      toast.success('Quiz submitted successfully!');
    } catch (error) {
      console.error('Quiz submission error:', error);
      toast.error('Failed to submit quiz');
    }
  };

  const backToQuizList = () => {
    setSelectedQuiz(null);
    setQuizResult(null);
    setQuizAnalysis(null);
    fetchQuizzes(); // Refresh quiz list
  };

  if (loading) return <div className="p-6">Loading quizzes...</div>;

  // Quiz Results View
  if (quizResult) {
    return (
      <div className="p-6 space-y-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Quiz Completed!</h2>
            <div className={`text-4xl font-bold mb-2 ${quizResult.percentage >= 70 ? 'text-green-600' : quizResult.percentage >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
              {quizResult.percentage.toFixed(1)}%
            </div>
            <p className="text-gray-600">{quizResult.score} out of {quizResult.total_marks} correct</p>
          </div>

          {/* AI Analysis Results */}
          {quizAnalysis && (
            <div className="mt-6 space-y-4">
              <h3 className="text-xl font-semibold text-gray-900">AI Analysis & Recommendations</h3>
              
              {quizAnalysis.analysis_data.performance_summary && (
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h4 className="font-medium text-blue-900 mb-2">Performance Summary</h4>
                  <p className="text-blue-800">{quizAnalysis.analysis_data.performance_summary}</p>
                </div>
              )}

              {quizAnalysis.insights && quizAnalysis.insights.length > 0 && (
                <div className="bg-green-50 p-4 rounded-lg">
                  <h4 className="font-medium text-green-900 mb-2">Key Insights</h4>
                  <ul className="text-green-800 space-y-1">
                    {quizAnalysis.insights.map((insight, idx) => (
                      <li key={idx}>• {insight}</li>
                    ))}
                  </ul>
                </div>
              )}

              {quizAnalysis.recommendations && quizAnalysis.recommendations.length > 0 && (
                <div className="bg-orange-50 p-4 rounded-lg">
                  <h4 className="font-medium text-orange-900 mb-2">Recommendations</h4>
                  <ul className="text-orange-800 space-y-1">
                    {quizAnalysis.recommendations.map((rec, idx) => (
                      <li key={idx}>• {rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="bg-purple-50 p-4 rounded-lg">
                <h4 className="font-medium text-purple-900 mb-2">Performance Trend</h4>
                <p className="text-purple-800 capitalize">{quizAnalysis.performance_trend}</p>
              </div>
            </div>
          )}

          <div className="flex space-x-4 mt-6">
            <button
              onClick={backToQuizList}
              className="flex-1 bg-emerald-500 text-white py-3 rounded-lg font-semibold hover:bg-emerald-600 transition-colors"
            >
              Back to Quizzes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Quiz Taking View
  if (selectedQuiz) {
    const question = selectedQuiz.questions[currentQuestion];
    const progress = ((currentQuestion + 1) / selectedQuiz.questions.length) * 100;

    return (
      <div className="p-6 space-y-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">{selectedQuiz.title}</h2>
            <button
              onClick={backToQuizList}
              className="text-gray-500 hover:text-gray-700"
            >
              ← Back
            </button>
          </div>

          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Question {currentQuestion + 1} of {selectedQuiz.questions.length}</span>
              <span>{progress.toFixed(0)}% Complete</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>

          {/* Question */}
          <div className="mb-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">{question.question}</h3>
            <div className="space-y-3">
              {question.options.map((option, optionIndex) => (
                <label key={optionIndex} className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="radio"
                    name={`question-${currentQuestion}`}
                    value={optionIndex}
                    checked={answers[currentQuestion] === optionIndex}
                    onChange={() => selectAnswer(currentQuestion, optionIndex)}
                    className="mr-3"
                  />
                  <span className="text-gray-800">{option}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Navigation */}
          <div className="flex justify-between">
            <button
              onClick={previousQuestion}
              disabled={currentQuestion === 0}
              className="px-6 py-2 bg-gray-300 text-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            
            {currentQuestion === selectedQuiz.questions.length - 1 ? (
              <button
                onClick={submitQuiz}
                className="px-6 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600"
              >
                Submit Quiz
              </button>
            ) : (
              <button
                onClick={nextQuestion}
                className="px-6 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600"
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Quiz List View
  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Available Quizzes</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {quizzes.length > 0 ? (
          quizzes.map((quiz, idx) => (
            <div key={quiz.id || idx} className="bg-white rounded-xl p-6 shadow-sm border hover:shadow-lg transition-shadow">
              <div className="mb-4">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{quiz.title}</h3>
                <p className="text-gray-600">{quiz.subject} • {quiz.grade_level}</p>
              </div>
              
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Questions:</span>
                  <span className="font-medium">{quiz.questions ? quiz.questions.length : 0}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Time Limit:</span>
                  <span className="font-medium">{quiz.time_limit || 30} min</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Total Marks:</span>
                  <span className="font-medium">{quiz.total_marks || (quiz.questions ? quiz.questions.length : 0)}</span>
                </div>
              </div>
              
              <button
                onClick={() => startQuiz(quiz)}
                className="w-full bg-emerald-500 text-white py-3 rounded-lg font-semibold hover:bg-emerald-600 transition-colors"
              >
                Take Quiz
              </button>
            </div>
          ))
        ) : (
          <div className="col-span-full text-center py-12">
            <PenTool className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 text-lg">No quizzes available</p>
            <p className="text-gray-400">Ask your teacher to create some quizzes</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Ask AI Component
const AskAI = () => {
  const [question, setQuestion] = useState('');
  const [subject, setSubject] = useState('Mathematics');
  const [gradeLevel, setGradeLevel] = useState('Grade 8');
  const [queryType, setQueryType] = useState('rag'); // 'rag' or 'general'
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState([]);
  const [availableMaterials, setAvailableMaterials] = useState([]);

  useEffect(() => {
    fetchAvailableMaterials();
  }, []);

  const fetchAvailableMaterials = async () => {
    try {
      const response = await axios.get('/api/materials/available');
      setAvailableMaterials(response.data.materials || []);
    } catch (error) {
      console.error('Failed to load materials:', error);
    }
  };

  const askQuestion = async () => {
    if (!question.trim()) return;

    setLoading(true);
    try {
      let response;
      
      if (queryType === 'rag') {
        // Use RAG system for course material-based answers
        response = await axios.post('/api/rag/ask', {
          question: question,
          subject: subject,
          grade_level: gradeLevel
        });
      } else {
        // Use general AI for broader questions
        response = await axios.post('/api/qa/ask', {
          question: question,
          subject: subject
        });
      }

      setConversation(prev => [
        ...prev,
        { 
          type: 'question', 
          text: question, 
          timestamp: new Date(),
          queryType: queryType
        },
        { 
          type: 'answer', 
          text: response.data.answer, 
          timestamp: new Date(),
          source: queryType === 'rag' ? 'course_materials' : 'ai_tutor'
        }
      ]);
      
      setQuestion('');
      toast.success('Question answered successfully!');
    } catch (error) {
      console.error('Question error:', error);
      toast.error('Failed to get answer');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Ask AI Tutor</h1>
        <p className="text-gray-600">Get answers from course materials or general AI tutoring</p>
      </div>

      {/* Available Materials Info */}
      {availableMaterials.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <h3 className="font-medium text-blue-900 mb-2">Available Course Materials</h3>
          <div className="space-y-1">
            {availableMaterials.slice(0, 3).map((material) => (
              <p key={material.id} className="text-blue-700 text-sm">
                📄 {material.original_filename} ({material.subject})
              </p>
            ))}
            {availableMaterials.length > 3 && (
              <p className="text-blue-700 text-sm">+ {availableMaterials.length - 3} more materials</p>
            )}
          </div>
        </div>
      )}

      {/* Question Input */}
      <div className="bg-white rounded-xl p-6 shadow-sm border space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Query Type</label>
            <select
              value={queryType}
              onChange={(e) => setQueryType(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="rag">Course Materials</option>
              <option value="general">General AI Tutor</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
            <select
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="Mathematics">Mathematics</option>
              <option value="Science">Science</option>
              <option value="English">English</option>
              <option value="History">History</option>
              <option value="Geography">Geography</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Grade Level</label>
            <select
              value={gradeLevel}
              onChange={(e) => setGradeLevel(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="Grade 6">Grade 6</option>
              <option value="Grade 7">Grade 7</option>
              <option value="Grade 8">Grade 8</option>
              <option value="Grade 9">Grade 9</option>
              <option value="Grade 10">Grade 10</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Your Question</label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={queryType === 'rag' 
              ? "Ask a question about your course materials..." 
              : "Ask any academic question..."}
            className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-emerald-500 min-h-[100px]"
          />
        </div>

        <button
          onClick={askQuestion}
          disabled={loading || !question.trim()}
          className="w-full bg-emerald-500 text-white py-3 rounded-lg font-semibold hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Getting Answer...' : (queryType === 'rag' ? 'Ask Course Materials' : 'Ask AI Tutor')}
        </button>
      </div>

      {/* Conversation History */}
      {conversation.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">Conversation</h2>
          <div className="space-y-4">
            {conversation.map((msg, idx) => (
              <div key={idx} className={`p-4 rounded-xl ${
                msg.type === 'question' 
                  ? 'bg-emerald-50 border-l-4 border-emerald-500' 
                  : 'bg-blue-50 border-l-4 border-blue-500'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-sm text-gray-600">
                      {msg.type === 'question' ? 'Your Question:' : 'AI Answer:'}
                    </span>
                    {msg.type === 'question' && (
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        msg.queryType === 'rag' 
                          ? 'bg-purple-100 text-purple-800' 
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {msg.queryType === 'rag' ? 'Course Materials' : 'AI Tutor'}
                      </span>
                    )}
                    {msg.type === 'answer' && msg.source && (
                      <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800">
                        {msg.source === 'course_materials' ? '📄 Course Materials' : '🤖 AI Tutor'}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-500">
                    {msg.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-gray-800 whitespace-pre-wrap">{msg.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Subscription Management Component  
const SubscriptionManagement = () => {
  const [subscription, setSubscription] = useState(null);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSubscriptionData();
  }, []);

  const fetchSubscriptionData = async () => {
    try {
      const [subResponse, plansResponse] = await Promise.all([
        axios.get('/my-subscription'),
        axios.get('/subscription-plans')
      ]);
      
      setSubscription(subResponse.data);
      setPlans(plansResponse.data.plans);
    } catch (error) {
      toast.error('Failed to load subscription data');
    } finally {
      setLoading(false);
    }
  };

  const subscribeToPlan = async (planId) => {
    try {
      // Create subscription order
      const response = await axios.post('/create-subscription', {
        student_id: 'current_user', // This would be handled by backend
        plan_id: planId,
        duration_months: 1
      });

      if (response.data.success) {
        // Initialize Razorpay payment
        const options = {
          key: response.data.key_id,
          amount: response.data.amount,
          currency: response.data.currency,
          name: 'EduAgent - Learning Platform',
          description: 'Monthly Premium Subscription',
          order_id: response.data.order_id,
          handler: async function (razorpayResponse) {
            try {
              // Verify payment
              await axios.post('/verify-payment', {
                order_id: razorpayResponse.razorpay_order_id,
                payment_id: razorpayResponse.razorpay_payment_id,
                signature: razorpayResponse.razorpay_signature
              });
              
              toast.success('Subscription activated successfully!');
              fetchSubscriptionData(); // Refresh subscription data
            } catch (error) {
              toast.error('Payment verification failed');
            }
          },
          prefill: {
            name: 'Student Name',
            email: 'student@example.com',
            contact: '9999999999'
          },
          theme: {
            color: '#10b981'
          }
        };

        const rzp = new window.Razorpay(options);
        rzp.open();
      }
    } catch (error) {
      toast.error('Failed to create subscription');
    }
  };

  if (loading) return <div className="p-6">Loading subscription data...</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Subscription Management</h1>
        <p className="text-gray-600">Manage your premium access to educational content</p>
      </div>

      {/* Current Subscription Status */}
      {subscription?.has_subscription ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-green-900">Premium Active</h3>
              <p className="text-green-700">You have access to all premium features</p>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            <p><span className="font-medium">Status:</span> {subscription.subscription.status}</p>
            <p><span className="font-medium">Expires:</span> {new Date(subscription.expires_at).toLocaleDateString()}</p>
            <p><span className="font-medium">Monthly Amount:</span> ₹{subscription.subscription.monthly_amount / 100}</p>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-yellow-900 mb-2">No Active Subscription</h3>
          <p className="text-yellow-700">Subscribe to access premium features and personalized learning</p>
        </div>
      )}

      {/* Available Plans */}
      <div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-4">Subscription Plans</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {plans.map((plan) => (
            <div key={plan.id} className="bg-white rounded-xl p-6 shadow-sm border hover:shadow-lg transition-shadow">
              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                <div className="text-3xl font-bold text-emerald-600 mb-2">{plan.price_display}</div>
                <p className="text-gray-600">{plan.description}</p>
              </div>

              <div className="space-y-3 mb-6">
                {plan.features.map((feature, idx) => (
                  <div key={idx} className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                    <span className="text-gray-700">{feature}</span>
                  </div>
                ))}
              </div>

              {!subscription?.has_subscription && (
                <button
                  onClick={() => subscribeToPlan(plan.id)}
                  className="w-full bg-emerald-500 text-white py-3 rounded-lg font-semibold hover:bg-emerald-600 transition-colors"
                >
                  Subscribe Now
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Personalized Learning Component
const PersonalizedLearning = () => {
  const [learningPath, setLearningPath] = useState(null);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLearningData();
  }, []);

  const fetchLearningData = async () => {
    try {
      const [pathResponse, insightsResponse] = await Promise.all([
        axios.get('/learning-path'),
        axios.get('/learning-insights')
      ]);
      
      setLearningPath(pathResponse.data);
      setInsights(insightsResponse.data.insights || []);
    } catch (error) {
      toast.error('Failed to load learning path');
    } finally {
      setLoading(false);
    }
  };

  const markTopicComplete = async (topic) => {
    try {
      await axios.post('/update-learning-progress', null, {
        params: { completed_topic: topic }
      });
      
      toast.success('Progress updated!');
      fetchLearningData(); // Refresh data
    } catch (error) {
      toast.error('Failed to update progress');
    }
  };

  if (loading) return <div className="p-6">Loading personalized learning path...</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Personalized Learning Path</h1>
        <p className="text-gray-600">AI-powered recommendations based on your performance</p>
      </div>

      {/* Current Level */}
      {learningPath && (
        <div className="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold mb-2">Current Level</h3>
              <p className="text-2xl font-bold capitalize">{learningPath.current_level}</p>
            </div>
            <Brain className="w-12 h-12 opacity-80" />
          </div>
        </div>
      )}

      {/* Learning Insights */}
      {insights.length > 0 && (
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">AI Insights</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.map((insight, idx) => (
              <div key={idx} className={`p-4 rounded-xl border-l-4 ${
                insight.priority === 'high' ? 'bg-red-50 border-red-500' :
                insight.priority === 'medium' ? 'bg-yellow-50 border-yellow-500' :
                'bg-blue-50 border-blue-500'
              }`}>
                <h4 className="font-semibold text-gray-900 mb-2">{insight.title}</h4>
                <p className="text-gray-700 text-sm">{insight.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Topics */}
      {learningPath && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Recommended Topics</h3>
            <div className="space-y-3">
              {learningPath.recommended_topics.map((topic, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="font-medium text-gray-900">{topic}</span>
                  <button
                    onClick={() => markTopicComplete(topic)}
                    className="px-3 py-1 bg-emerald-500 text-white rounded text-sm hover:bg-emerald-600"
                  >
                    Mark Complete
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-6">
            {/* Strong Areas */}
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <h3 className="text-lg font-semibold text-green-900 mb-4">Strong Areas</h3>
              <div className="space-y-2">
                {learningPath.strong_areas.map((area, idx) => (
                  <div key={idx} className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-gray-700">{area}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Areas for Improvement */}
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <h3 className="text-lg font-semibold text-orange-900 mb-4">Areas for Improvement</h3>
              <div className="space-y-2">
                {learningPath.weak_areas.map((area, idx) => (
                  <div key={idx} className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                    <span className="text-gray-700">{area}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Create Content Component (for teachers)
const CreateContent = () => {
  const [formData, setFormData] = useState({
    title: '',
    subject: 'Mathematics',
    grade_level: 'Grade 8',
    topic: '',
    tags: []
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await axios.post('/study/generate', formData);
      toast.success('Content generated successfully!');
      setFormData({
        title: '',
        subject: 'Mathematics', 
        grade_level: 'Grade 8',
        topic: '',
        tags: []
      });
    } catch (error) {
      toast.error('Failed to generate content');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Create Study Content</h1>
      
      <form onSubmit={handleSubmit} className="bg-white rounded-xl p-6 shadow-sm border space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Content Title</label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => setFormData({...formData, title: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
            <select
              value={formData.subject}
              onChange={(e) => setFormData({...formData, subject: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="Mathematics">Mathematics</option>
              <option value="Science">Science</option>
              <option value="English">English</option>
              <option value="History">History</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Grade Level</label>
            <select
              value={formData.grade_level}
              onChange={(e) => setFormData({...formData, grade_level: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="Grade 6">Grade 6</option>
              <option value="Grade 7">Grade 7</option>
              <option value="Grade 8">Grade 8</option>
              <option value="Grade 9">Grade 9</option>
              <option value="Grade 10">Grade 10</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Topic Description</label>
          <textarea
            value={formData.topic}
            onChange={(e) => setFormData({...formData, topic: e.target.value})}
            placeholder="Describe the topic you want to generate content for..."
            className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-emerald-500 min-h-[100px]"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-emerald-500 text-white py-3 rounded-lg font-semibold hover:bg-emerald-600 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Generating Content...' : 'Generate AI Content'}
        </button>
      </form>
    </div>
  );
};

// Create Quiz Component (for teachers)
const CreateQuiz = () => {
  const [formData, setFormData] = useState({
    title: '',
    subject: 'Mathematics',
    grade_level: 'Grade 8',
    topic: '',
    num_questions: 10,
    difficulty: 'medium'
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await axios.post('/quiz/generate', formData);
      toast.success('Quiz generated successfully!');
      setFormData({
        title: '',
        subject: 'Mathematics',
        grade_level: 'Grade 8', 
        topic: '',
        num_questions: 10,
        difficulty: 'medium'
      });
    } catch (error) {
      toast.error('Failed to generate quiz');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Create Quiz</h1>
      
      <form onSubmit={handleSubmit} className="bg-white rounded-xl p-6 shadow-sm border space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Quiz Title</label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => setFormData({...formData, title: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
            <select
              value={formData.subject}
              onChange={(e) => setFormData({...formData, subject: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="Mathematics">Mathematics</option>
              <option value="Science">Science</option>
              <option value="English">English</option>
              <option value="History">History</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Grade Level</label>
            <select
              value={formData.grade_level}
              onChange={(e) => setFormData({...formData, grade_level: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="Grade 6">Grade 6</option>
              <option value="Grade 7">Grade 7</option>
              <option value="Grade 8">Grade 8</option>
              <option value="Grade 9">Grade 9</option>
              <option value="Grade 10">Grade 10</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Quiz Topic</label>
          <textarea
            value={formData.topic}
            onChange={(e) => setFormData({...formData, topic: e.target.value})}
            placeholder="Describe the topic for quiz questions..."
            className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-emerald-500 min-h-[100px]"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Number of Questions</label>
            <select
              value={formData.num_questions}
              onChange={(e) => setFormData({...formData, num_questions: parseInt(e.target.value)})}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value={5}>5 Questions</option>
              <option value={10}>10 Questions</option>
              <option value={15}>15 Questions</option>
              <option value={20}>20 Questions</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Difficulty</label>
            <select
              value={formData.difficulty}
              onChange={(e) => setFormData({...formData, difficulty: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-emerald-500 text-white py-3 rounded-lg font-semibold hover:bg-emerald-600 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Generating Quiz...' : 'Generate AI Quiz'}
        </button>
      </form>
    </div>
  );
};

// Students Management Component (for teachers)
const StudentsManagement = () => {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Students Management</h1>
      <div className="bg-white rounded-xl p-8 shadow-sm border text-center">
        <Users className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-500 text-lg">Student management features</p>
        <p className="text-gray-400">Coming soon in next update</p>
      </div>
    </div>
  );
};

// File Upload Component (for teachers)
const FileUpload = () => {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    subject: 'Mathematics',
    grade_level: 'Grade 8',
    description: ''
  });

  useEffect(() => {
    fetchMaterials();
  }, []);

  const fetchMaterials = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/teacher/my-materials');
      setMaterials(response.data.materials || []);
    } catch (error) {
      toast.error('Failed to load materials');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Please upload only PDF files');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('subject', uploadForm.subject);
      formData.append('grade_level', uploadForm.grade_level);
      formData.append('description', uploadForm.description || `Study material: ${file.name}`);

      const response = await axios.post('/api/teacher/upload-material', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast.success(`File uploaded and processed! ${response.data.pages_processed} pages extracted.`);
      fetchMaterials();
      setUploadForm({ subject: 'Mathematics', grade_level: 'Grade 8', description: '' });
      event.target.value = ''; // Reset file input
    } catch (error) {
      toast.error('Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Study Materials</h1>
        <p className="text-gray-600">Upload PDF course materials for AI-powered Q&A system</p>
      </div>

      {/* Upload Form */}
      <div className="bg-white rounded-xl p-6 shadow-sm border">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload New Material</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
            <select
              value={uploadForm.subject}
              onChange={(e) => setUploadForm({...uploadForm, subject: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="Mathematics">Mathematics</option>
              <option value="Science">Science</option>
              <option value="English">English</option>
              <option value="History">History</option>
              <option value="Geography">Geography</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Grade Level</label>
            <select
              value={uploadForm.grade_level}
              onChange={(e) => setUploadForm({...uploadForm, grade_level: e.target.value})}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
            >
              <option value="Grade 6">Grade 6</option>
              <option value="Grade 7">Grade 7</option>
              <option value="Grade 8">Grade 8</option>
              <option value="Grade 9">Grade 9</option>
              <option value="Grade 10">Grade 10</option>
            </select>
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Description (Optional)</label>
          <input
            type="text"
            value={uploadForm.description}
            onChange={(e) => setUploadForm({...uploadForm, description: e.target.value})}
            placeholder="Brief description of the material..."
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Upload PDF File</label>
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileUpload}
            disabled={uploading}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100"
          />
        </div>

        {uploading && (
          <div className="text-center text-emerald-600">
            <p>Processing file and creating embeddings...</p>
          </div>
        )}
      </div>

      {/* Uploaded Materials */}
      <div className="bg-white rounded-xl p-6 shadow-sm border">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">My Uploaded Materials</h3>
        
        {loading ? (
          <p className="text-gray-500">Loading materials...</p>
        ) : materials.length > 0 ? (
          <div className="grid gap-4">
            {materials.map((material) => (
              <div key={material.id} className="border rounded-lg p-4 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900">{material.original_filename}</h4>
                    <p className="text-gray-600 text-sm">{material.subject} • {material.grade_level}</p>
                    <p className="text-gray-500 text-sm">{material.description}</p>
                  </div>
                  <div className="text-right">
                    <div className={`px-2 py-1 rounded-full text-xs ${
                      material.is_processed 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {material.is_processed ? '✅ Processed' : '⏳ Processing'}
                    </div>
                    <p className="text-gray-500 text-xs mt-1">
                      {(material.file_size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No materials uploaded yet</p>
        )}
      </div>
    </div>
  );
};

// Notes Component (for students)
const NotesManager = () => {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newNote, setNewNote] = useState({
    title: '',
    content: '',
    subject: 'Mathematics',
    tags: []
  });
  const [summarizing, setSummarizing] = useState(false);
  const [summaryResult, setSummaryResult] = useState(null);

  useEffect(() => {
    fetchNotes();
  }, []);

  const fetchNotes = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/notes/my-notes');
      setNotes(response.data.notes || []);
    } catch (error) {
      toast.error('Failed to load notes');
    } finally {
      setLoading(false);
    }
  };

  const createNote = async () => {
    if (!newNote.title.trim() || !newNote.content.trim()) {
      toast.error('Please provide both title and content');
      return;
    }

    try {
      await axios.post('/api/notes/create', newNote);
      toast.success('Note created successfully!');
      setNewNote({ title: '', content: '', subject: 'Mathematics', tags: [] });
      setShowCreateForm(false);
      fetchNotes();
    } catch (error) {
      toast.error('Failed to create note');
    }
  };

  const summarizeNote = async (noteContent, summaryType = 'brief') => {
    setSummarizing(true);
    try {
      const response = await axios.post('/api/notes/summarize', {
        note_content: noteContent,
        summary_type: summaryType
      });
      
      setSummaryResult({
        ...response.data,
        original_content: noteContent
      });
      
      toast.success('Note summarized successfully!');
    } catch (error) {
      toast.error('Failed to summarize note');
    } finally {
      setSummarizing(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">My Notes</h1>
          <p className="text-gray-600">Create, manage, and summarize your study notes</p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="bg-emerald-500 text-white px-4 py-2 rounded-lg hover:bg-emerald-600 transition-colors"
        >
          {showCreateForm ? 'Cancel' : 'Create Note'}
        </button>
      </div>

      {/* Create Note Form */}
      {showCreateForm && (
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Create New Note</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Title</label>
              <input
                type="text"
                value={newNote.title}
                onChange={(e) => setNewNote({...newNote, title: e.target.value})}
                placeholder="Note title..."
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
              <select
                value={newNote.subject}
                onChange={(e) => setNewNote({...newNote, subject: e.target.value})}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
              >
                <option value="Mathematics">Mathematics</option>
                <option value="Science">Science</option>
                <option value="English">English</option>
                <option value="History">History</option>
                <option value="Geography">Geography</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Content</label>
              <textarea
                value={newNote.content}
                onChange={(e) => setNewNote({...newNote, content: e.target.value})}
                placeholder="Write your notes here..."
                className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-emerald-500 min-h-[200px]"
              />
            </div>

            <div className="flex space-x-2">
              <button
                onClick={createNote}
                className="bg-emerald-500 text-white px-6 py-2 rounded-lg hover:bg-emerald-600 transition-colors"
              >
                Save Note
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                className="bg-gray-300 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-400 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Summary Result */}
      {summaryResult && (
        <div className="bg-white rounded-xl p-6 shadow-sm border">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">AI Summary</h3>
            <button
              onClick={() => setSummaryResult(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
          
          <div className="bg-blue-50 p-4 rounded-lg mb-4">
            <h4 className="font-medium text-blue-900 mb-2">Summary ({summaryResult.summary_type})</h4>
            <p className="text-blue-800 whitespace-pre-wrap">{summaryResult.summary}</p>
          </div>
          
          <div className="text-sm text-gray-600">
            Original: {summaryResult.original_length} characters → Summary: {summaryResult.summary.length} characters
            ({((summaryResult.summary.length / summaryResult.original_length) * 100).toFixed(1)}% of original)
          </div>
        </div>
      )}

      {/* Notes List */}
      <div className="space-y-4">
        {loading ? (
          <p className="text-gray-500">Loading notes...</p>
        ) : notes.length > 0 ? (
          notes.map((note) => (
            <div key={note.id} className="bg-white rounded-xl p-6 shadow-sm border">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">{note.title}</h3>
                  <p className="text-gray-600 text-sm">{note.subject} • {new Date(note.created_at).toLocaleDateString()}</p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => summarizeNote(note.content, 'brief')}
                    disabled={summarizing}
                    className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50"
                  >
                    Brief Summary
                  </button>
                  <button
                    onClick={() => summarizeNote(note.content, 'detailed')}
                    disabled={summarizing}
                    className="px-3 py-1 bg-purple-500 text-white text-sm rounded hover:bg-purple-600 disabled:opacity-50"
                  >
                    Detailed Summary
                  </button>
                </div>
              </div>
              
              <div className="text-gray-700 whitespace-pre-wrap mb-3">
                {note.content.length > 300 
                  ? `${note.content.substring(0, 300)}...` 
                  : note.content
                }
              </div>
              
              {note.tags && note.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {note.tags.map((tag, idx) => (
                    <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">No notes yet</p>
            <p className="text-gray-400">Create your first note to get started</p>
          </div>
        )}
      </div>

      {summarizing && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg">
            <p className="text-gray-900">Summarizing note with AI...</p>
          </div>
        </div>
      )}
    </div>
  );
};

// My Children Component (for parents)
const MyChildren = () => {
  const [children, setChildren] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchChildren();
  }, []);

  const fetchChildren = async () => {
    try {
      const response = await axios.get('/api/parent/students');
      setChildren(response.data.students);
    } catch (error) {
      toast.error('Failed to load children data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-6">Loading children data...</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">My Children</h1>
        <p className="text-gray-600">Monitor your children's educational progress</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {children.map((child) => (
          <div key={child.id} className="bg-white rounded-xl p-6 shadow-sm border hover:shadow-lg transition-shadow">
            <div className="flex items-center space-x-4 mb-4">
              <div className="w-12 h-12 bg-emerald-500 rounded-full flex items-center justify-center">
                <User className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">{child.name}</h3>
                <p className="text-gray-600 text-sm">{child.email}</p>
              </div>
            </div>
            
            <div className="space-y-2 text-sm mb-4">
              <p><span className="font-medium">Student ID:</span> {child.id}</p>
              <p><span className="font-medium">Role:</span> {child.role}</p>
              <p><span className="font-medium">Joined:</span> {new Date(child.created_at).toLocaleDateString()}</p>
            </div>
            
            <button className="w-full bg-emerald-500 text-white py-2 rounded-lg hover:bg-emerald-600 transition-colors">
              View Progress
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

// Progress Reports Component (for parents)
const ProgressReports = () => {
  const [selectedChild, setSelectedChild] = useState('');
  const [children, setChildren] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchChildren();
  }, []);

  const fetchChildren = async () => {
    try {
      const response = await axios.get('/parent/students');
      setChildren(response.data.students);
    } catch (error) {
      toast.error('Failed to load children');
    }
  };

  const generateReport = async () => {
    if (!selectedChild) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`/parent/progress-report/${selectedChild}`);
      setReport(response.data);
    } catch (error) {
      toast.error('Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Progress Reports</h1>
        <p className="text-gray-600">Generate comprehensive progress reports for your children</p>
      </div>

      {/* Child Selection */}
      <div className="bg-white rounded-xl p-6 shadow-sm border">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Child</h3>
        <div className="flex gap-4">
          <select
            value={selectedChild}
            onChange={(e) => setSelectedChild(e.target.value)}
            className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">Select a child...</option>
            {children.map((child) => (
              <option key={child.id} value={child.id}>{child.name}</option>
            ))}
          </select>
          <button
            onClick={generateReport}
            disabled={!selectedChild || loading}
            className="px-6 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Generating...' : 'Generate Report'}
          </button>
        </div>
      </div>

      {/* Progress Report Display */}
      {report && (
        <div className="space-y-6">
          {/* Student Info */}
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Student Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Name</p>
                <p className="font-medium">{report.student_info.name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Email</p>
                <p className="font-medium">{report.student_info.email}</p>
              </div>
            </div>
          </div>

          {/* Overall Performance */}
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Overall Performance</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-emerald-600">{report.overall_performance.total_quizzes}</p>
                <p className="text-gray-600">Quizzes Taken</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600">{report.overall_performance.average_score}%</p>
                <p className="text-gray-600">Average Score</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-600">{report.overall_performance.total_questions_asked}</p>
                <p className="text-gray-600">Questions Asked</p>
              </div>
              <div className="text-center">
                <p className={`text-2xl font-bold ${report.overall_performance.performance_trend === 'improving' ? 'text-green-600' : 'text-orange-600'}`}>
                  {report.overall_performance.performance_trend === 'improving' ? '↗️' : '⚠️'}
                </p>
                <p className="text-gray-600">Trend</p>
              </div>
            </div>
          </div>

          {/* Subject Performance */}
          {Object.keys(report.subject_performance || {}).length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Subject Performance</h3>
              <div className="space-y-4">
                {Object.entries(report.subject_performance).map(([subject, stats]) => (
                  <div key={subject} className="p-4 bg-gray-50 rounded-lg">
                    <div className="flex justify-between items-center mb-2">
                      <h4 className="font-medium text-gray-900">{subject}</h4>
                      <span className="text-lg font-bold text-emerald-600">{stats.average_score.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between text-sm text-gray-600">
                      <span>Attempts: {stats.attempts}</span>
                      <span>Latest: {stats.latest_score}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Insights */}
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">AI Insights & Recommendations</h3>
            <div className="prose max-w-none">
              <p className="text-gray-700">{report.ai_insights}</p>
            </div>
          </div>

          {/* Learning Path */}
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Learning Assessment</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Current Level</h4>
                <p className="text-emerald-600 font-semibold capitalize">{report.learning_path.current_level}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Strong Areas</h4>
                <div className="space-y-1">
                  {report.learning_path.strong_areas.map((area, idx) => (
                    <p key={idx} className="text-green-600 text-sm">{area}</p>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Improvement Areas</h4>
                <div className="space-y-1">
                  {report.learning_path.weak_areas.map((area, idx) => (
                    <p key={idx} className="text-orange-600 text-sm">{area}</p>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Main Dashboard Component
const Dashboard = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        if (user?.role === 'student') return <StudentDashboard />;
        if (user?.role === 'teacher') return <TeacherDashboard />;
        if (user?.role === 'parent') return <ParentDashboard />;
        break;
      case 'study':
        return <StudyContent />;
      case 'quiz':
        return <QuizSystem />;
      case 'ask':
        return <AskAI />;
      case 'create-content':
        return <CreateContent />;
      case 'create-quiz':
        return <CreateQuiz />;
      case 'students':
        return <StudentsManagement />;
      case 'children':
        return <MyChildren />;
      case 'progress':
        return <ProgressReports />;
      case 'subscription':
        return <SubscriptionManagement />;
      case 'learning-path':
        return <PersonalizedLearning />;
      case 'chat':
        return <div className="p-6">Messages - Coming Soon (WhatsApp Integration)</div>;
      default:
        return <div className="p-6">Page not found</div>;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        user={user}
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
      />
      
      <div className="flex-1 lg:ml-0">
        {/* Mobile Header */}
        <div className="lg:hidden bg-white shadow-sm border-b px-4 py-3">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setIsMobileOpen(true)}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <Menu className="w-6 h-6" />
            </button>
            <h1 className="font-semibold">EduAgent</h1>
            <div className="w-10" /> {/* Spacer */}
          </div>
        </div>
        
        <main className="min-h-screen">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};

// Loading Component
const Loading = () => (
  <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 flex items-center justify-center">
    <div className="text-center">
      <div className="w-16 h-16 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-2xl flex items-center justify-center mx-auto mb-4 animate-pulse">
        <Brain className="w-8 h-8 text-white" />
      </div>
      <p className="text-gray-600">Loading EduAgent...</p>
    </div>
  </div>
);

// Main App Component
function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/*" element={<AppContent />} />
        </Routes>
        <Toaster 
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#fff',
              color: '#363636',
              borderRadius: '12px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
            },
          }}
        />
      </BrowserRouter>
    </AuthProvider>
  );
}

const AppContent = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return <Loading />;
  }

  return (
    <Routes>
      <Route 
        path="/*" 
        element={user ? <Dashboard /> : <Login />} 
      />
    </Routes>
  );
};

export default App;
