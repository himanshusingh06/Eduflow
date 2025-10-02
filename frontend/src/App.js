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
        { id: 'ask', label: 'Ask Question', icon: Brain },
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
        return <div className="p-6">Study Content - Coming Soon</div>;
      case 'quiz':
        return <div className="p-6">Quizzes - Coming Soon</div>;
      case 'ask':
        return <div className="p-6">Ask AI Question - Coming Soon</div>;
      case 'create-content':
        return <div className="p-6">Create Content - Coming Soon</div>;
      case 'create-quiz':
        return <div className="p-6">Create Quiz - Coming Soon</div>;
      case 'students':
        return <div className="p-6">Students Management - Coming Soon</div>;
      case 'children':
        return <div className="p-6">My Children - Coming Soon</div>;
      case 'progress':
        return <div className="p-6">Progress Reports - Coming Soon</div>;
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
