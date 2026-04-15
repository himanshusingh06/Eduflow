import React, { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import toast from "react-hot-toast";
import {
  ArrowRight,
  BookOpen,
  Bot,
  Brain,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  GraduationCap,
  Library,
  LineChart,
  Mail,
  MapPin,
  Menu,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
  X,
} from "lucide-react";
import edumatelogo from "../assets/edumale_logo.jpg";

const navItems = [
  { id: "about", label: "About" },
  { id: "features", label: "Features" },
  { id: "workflow", label: "How It Works" },
  { id: "community", label: "Who It Helps" },
  { id: "contact", label: "Contact" },
];

const heroHighlights = [
  {
    label: "AI Tutor Support",
    value: "Ask doubts and clarify concepts",
    description: "Students can ask questions, understand difficult topics faster, and keep moving instead of getting stuck.",
  },
  {
    label: "Assessment Tools",
    value: "Quizzes, custom quizzes, evaluation",
    description: "The platform supports structured practice so understanding can be measured, reviewed, and improved.",
  },
  {
    label: "Learning Workspace",
    value: "Notes, PDFs, progress, planning",
    description: "Study material, revision tools, and progress visibility stay connected in one academic environment.",
  },
];

const aboutCards = [
  {
    icon: Brain,
    title: "Built for day-to-day learning",
    description:
      "EduMate supports the real flow of study: understanding concepts, solving doubts, practicing through quizzes, and returning to weak areas with more structure.",
  },
  {
    icon: BookOpen,
    title: "One place instead of many tools",
    description:
      "Content, quizzes, notes, PDFs, and progress should not be scattered. The platform brings these academic actions together so the experience feels more continuous.",
  },
  {
    icon: Users,
    title: "Useful for every role",
    description:
      "Students, teachers, parents, and administrators each get a focused experience while still staying connected to the same broader learning journey.",
  },
  {
    icon: ShieldCheck,
    title: "Structured and dependable",
    description:
      "Role-based dashboards, verified access, and organized navigation help the platform feel cleaner, safer, and easier to trust from the first login.",
  },
];

const featureCards = [
  {
    icon: Bot,
    title: "Ask AI Tutor",
    description:
      "The AI tutor helps students ask doubts naturally, understand concepts in simpler language, and continue learning without losing momentum.",
    details: [
      "Useful for immediate doubt solving during study sessions.",
      "Supports revision before tests and quizzes.",
      "Turns question asking into a routine part of learning.",
    ],
  },
  {
    icon: ClipboardCheck,
    title: "Quizzes and Custom Quiz Generation",
    description:
      "EduMate supports prepared quizzes and custom AI-generated quizzes, helping students practice by subject, chapter, or specific topic.",
    details: [
      "Teachers can create structured assessments.",
      "Students can generate focused practice on demand.",
      "Evaluation helps convert attempts into useful feedback.",
    ],
  },
  {
    icon: Library,
    title: "Study Content and Teaching Material",
    description:
      "Teachers can create study content, upload materials, and keep resources organized so learning content is available inside the same platform.",
    details: [
      "Useful for lesson support and revision material.",
      "Keeps study resources connected to quizzes and practice.",
      "Helps institutions maintain a more consistent academic workflow.",
    ],
  },
  {
    icon: FileText,
    title: "Notes, PDFs, and Revision Support",
    description:
      "Students can maintain notes, work with PDFs, and keep important study material inside the same environment where they revise and practice.",
    details: [
      "Reduces scattered study material across apps.",
      "Makes revision easier over time.",
      "Supports a more organized personal study routine.",
    ],
  },
  {
    icon: LineChart,
    title: "Dashboards and Progress Visibility",
    description:
      "Progress is visible across the platform through dashboards, reports, and performance summaries that help users make better academic decisions.",
    details: [
      "Students can track activity and improvement.",
      "Teachers get better visibility into participation and performance.",
      "Parents can understand progress more clearly.",
    ],
  },
  {
    icon: Workflow,
    title: "Connected Role-Based Workflows",
    description:
      "The strongest feature of EduMate is how its modules work together. Study, practice, review, and reporting all support one another.",
    details: [
      "Students get a smoother path from learning to practice.",
      "Teachers manage content and assessment in one system.",
      "Parents and admins get clearer academic visibility.",
    ],
  },
];

const workflowSteps = [
  {
    step: "01",
    title: "Choose the right role and enter a focused dashboard",
    description:
      "Students, teachers, parents, and administrators each begin with an experience designed for their responsibilities rather than a one-size-fits-all interface.",
  },
  {
    step: "02",
    title: "Learn, create, ask, or upload in one place",
    description:
      "Students study and revise, teachers create content and quizzes, and institutions keep resources organized in one connected platform.",
  },
  {
    step: "03",
    title: "Practice and review through structured assessment",
    description:
      "Quizzes and evaluations help turn learning into measurable progress, so users understand where performance is strong and where more work is needed.",
  },
  {
    step: "04",
    title: "Use visibility to improve consistency over time",
    description:
      "Because activity, materials, and reports remain connected, users can build stronger routines and make better academic decisions over the long term.",
  },
];

const audienceCards = [
  {
    icon: GraduationCap,
    title: "Students",
    description:
      "Students get a guided environment for understanding concepts, practicing through quizzes, managing notes, and staying more consistent with revision.",
    points: [
      "Ask doubts and get guided answers.",
      "Practice with regular and custom quizzes.",
      "Keep notes, PDFs, and progress in one place.",
    ],
  },
  {
    icon: BookOpen,
    title: "Teachers",
    description:
      "Teachers can create content, build quizzes, upload learning material, and track activity with less manual effort and better academic continuity.",
    points: [
      "Create and manage study content faster.",
      "Build structured quizzes for students.",
      "Monitor student participation more clearly.",
    ],
  },
  {
    icon: Users,
    title: "Parents",
    description:
      "Parents get better visibility into learning progress and can support children with more confidence because the academic picture is easier to understand.",
    points: [
      "Review progress and performance more clearly.",
      "Understand where support may be needed.",
      "Stay connected to the child’s learning journey.",
    ],
  },
];

const platformModules = [
  {
    title: "Student Workspace",
    description:
      "Includes study content, quizzes, custom quizzes, AI tutor support, notes, PDFs, learning path tools, and subscription access in one dashboard.",
  },
  {
    title: "Teacher Workspace",
    description:
      "Includes content creation, quiz creation, material upload, and student-facing academic management so teaching workflows stay more organized.",
  },
  {
    title: "Parent and Admin Visibility",
    description:
      "Parents can review progress and child activity, while administrators can manage users, access, and subscriptions across the platform.",
  },
];

const footerColumns = [
  {
    title: "Platform",
    links: [
      { label: "About EduMate", type: "scroll", href: "about" },
      { label: "Features", type: "scroll", href: "features" },
      { label: "How It Works", type: "scroll", href: "workflow" },
      { label: "Who It Helps", type: "scroll", href: "community" },
    ],
  },
  {
    title: "Access",
    links: [
      { label: "Login", type: "route", href: "/login" },
      { label: "Sign Up", type: "route", href: "/signup" },
      { label: "Contact Us", type: "scroll", href: "contact" },
      { label: "Platform Modules", type: "scroll", href: "modules" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Ask AI Tutor", type: "scroll", href: "features" },
      { label: "Custom Quiz", type: "scroll", href: "features" },
      { label: "Progress Reports", type: "scroll", href: "community" },
      { label: "Study Workflows", type: "scroll", href: "workflow" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", type: "route", href: "/privacy-policy" },
      { label: "Terms and Conditions", type: "route", href: "/terms-and-conditions" },
      { label: "Refund Policy", type: "route", href: "/refund-policy" },
    ],
  },
];

const trustSignals = [
  "Role-based dashboards for students, teachers, parents, and administrators",
  "Secure login with account verification and structured access control",
  "Mobile-friendly and desktop-friendly experience aligned with the core app theme",
  "One platform for study support, practice, reports, notes, and communication",
];

const extractContactErrorState = (error) => {
  const responseData = error?.response?.data;
  const fallbackMessage = "Unable to send your message right now. Please try again.";
  const fieldLabels = {
    full_name: "Full name",
    email: "Email",
    phone: "Phone",
    role: "Role",
    institution: "Institution",
    subject: "Subject",
    message: "Message",
  };

  if (!responseData) {
    return { message: fallbackMessage, fieldErrors: {} };
  }

  const fieldErrors = Array.isArray(responseData.errors)
    ? responseData.errors.reduce((accumulator, item) => {
        if (item?.field && item.field !== "form" && typeof item.message === "string") {
          const label = fieldLabels[item.field] || item.field;
          accumulator[item.field] = `${label}: ${item.message}`;
        }
        return accumulator;
      }, {})
    : {};

  if (typeof responseData.detail === "string") {
    return { message: responseData.detail, fieldErrors };
  }

  if (responseData.detail && typeof responseData.detail.message === "string") {
    return { message: responseData.detail.message, fieldErrors };
  }

  if (Array.isArray(responseData.detail)) {
    const firstMessage = responseData.detail.find((item) => typeof item?.msg === "string")?.msg;
    return { message: firstMessage || fallbackMessage, fieldErrors };
  }

  if (typeof responseData.message === "string") {
    return { message: responseData.message, fieldErrors };
  }

  return { message: fallbackMessage, fieldErrors };
};

const SectionTitle = ({ eyebrow, title, description }) => (
  <div className="max-w-4xl">
    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">{eyebrow}</p>
    <h2 className="mt-3 text-3xl font-bold text-slate-900 sm:text-4xl">{title}</h2>
    <p className="mt-4 text-base leading-8 text-slate-600 sm:text-lg">{description}</p>
  </div>
);

function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionState, setSubmissionState] = useState({ type: "", message: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    phone: "",
    role: "student",
    institution: "",
    subject: "",
    message: "",
  });

  const scrollTo = (id) => {
    const section = document.getElementById(id);
    if (section) {
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    setMobileMenuOpen(false);
  };

  const handleChange = (field, value) => {
    setFieldErrors((prev) => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
    if (submissionState.type === "error") {
      setSubmissionState({ type: "", message: "" });
    }
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    setSubmissionState({ type: "", message: "" });
    setFieldErrors({});

    const payload = {
      full_name: formData.full_name.trim(),
      email: formData.email.trim(),
      phone: formData.phone.trim(),
      role: formData.role,
      institution: formData.institution.trim(),
      subject: formData.subject.trim(),
      message: formData.message.trim(),
    };

    try {
      const response = await axios.post("/contact", payload);
      const successMessage = response?.data?.message || "Your message has been sent successfully.";
      toast.success(successMessage);
      setSubmissionState({ type: "success", message: successMessage });
      setFormData({
        full_name: "",
        email: "",
        phone: "",
        role: "student",
        institution: "",
        subject: "",
        message: "",
      });
    } catch (error) {
      const { message, fieldErrors: nextFieldErrors } = extractContactErrorState(error);
      setFieldErrors(nextFieldErrors);
      setSubmissionState({ type: "error", message });
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getInputClassName = (field) =>
    `w-full rounded-2xl border px-4 py-3 text-sm focus:outline-none focus:ring-2 ${
      fieldErrors[field]
        ? "border-red-300 focus:border-red-400 focus:ring-red-200"
        : "border-slate-200 focus:border-emerald-400 focus:ring-emerald-200"
    }`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 text-slate-900">
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.20),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(13,148,136,0.16),transparent_36%)]" />
        <div className="absolute left-[-10rem] top-28 h-72 w-72 rounded-full bg-emerald-200/40 blur-3xl" />
        <div className="absolute bottom-16 right-[-6rem] h-64 w-64 rounded-full bg-cyan-200/40 blur-3xl" />
      </div>

      <header className="sticky top-0 z-40 border-b border-emerald-100 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} className="flex items-center gap-3 text-left">
            <div className="h-12 w-12 overflow-hidden rounded-xl ring-1 ring-emerald-200">
              <img src={edumatelogo} alt="EduMate" className="h-full w-full object-cover" />
            </div>
            <div>
              <p className="text-sm font-bold text-emerald-700">EduMate</p>
              <p className="text-xs text-slate-500">AI-powered learning platform</p>
            </div>
          </button>

          <nav className="hidden items-center gap-2 lg:flex">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => scrollTo(item.id)}
                className="rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-emerald-50 hover:text-emerald-700"
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="hidden items-center gap-2 lg:flex">
            <Link to="/login" className="rounded-full border border-emerald-200 px-4 py-2 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50">
              Login
            </Link>
            <Link to="/signup" className="rounded-full bg-gradient-to-r from-emerald-500 to-teal-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:from-emerald-600 hover:to-teal-700">
              Sign Up
            </Link>
          </div>

          <button
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="rounded-xl border border-emerald-200 p-2 text-emerald-700 lg:hidden"
            aria-label="Toggle navigation"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="border-t border-emerald-100 bg-white px-4 py-3 lg:hidden">
            <div className="space-y-1">
              {navItems.map((item) => (
                <button
                  key={`mobile-${item.id}`}
                  onClick={() => scrollTo(item.id)}
                  className="block w-full rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-600 hover:bg-emerald-50 hover:text-emerald-700"
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <Link to="/login" className="rounded-xl border border-emerald-200 px-3 py-2 text-center text-sm font-semibold text-emerald-700">
                Login
              </Link>
              <Link to="/signup" className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-3 py-2 text-center text-sm font-semibold text-white">
                Sign Up
              </Link>
            </div>
          </div>
        )}
      </header>

      <main className="mx-auto max-w-7xl px-4 sm:px-6">
        <section className="grid gap-10 py-12 lg:grid-cols-[1.1fr_0.9fr] lg:py-20">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700 shadow-sm">
              <Sparkles className="h-4 w-4" />
              AI-powered learning platform for students, teachers, and parents
            </div>
            <h1 className="mt-6 text-4xl font-bold leading-tight text-slate-900 sm:text-6xl">
              One connected platform for study, practice, progress tracking, and academic support.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              EduMate helps students learn with more clarity, helps teachers create and manage academic work more efficiently, and helps parents stay
              informed with better visibility into progress. Instead of separating doubts, content, quizzes, notes, and reports, the platform keeps them connected.
            </p>
            <p className="mt-4 max-w-2xl text-base leading-8 text-slate-600">
              The result is a more practical learning system where users can move from understanding to practice, from practice to review, and from
              review to better academic decisions without losing context.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/signup" className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-emerald-500 to-teal-600 px-6 py-3 text-sm font-semibold text-white shadow transition hover:from-emerald-600 hover:to-teal-700">
                Create your account
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/login" className="rounded-full border border-emerald-200 bg-white px-6 py-3 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-50">
                Go to login
              </Link>
            </div>
            <div className="mt-10 grid gap-3 sm:grid-cols-2">
              {trustSignals.map((signal) => (
                <div key={signal} className="flex items-start gap-3 rounded-2xl border border-emerald-100 bg-white/85 p-4 shadow-sm">
                  <ShieldCheck className="mt-0.5 h-5 w-5 text-emerald-600" />
                  <p className="text-sm leading-6 text-slate-600">{signal}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 self-start">
            <div className="rounded-[28px] border border-emerald-100 bg-white p-6 shadow-lg shadow-emerald-100/70">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-700">Core platform strengths</p>
              <div className="mt-5 grid gap-4">
                {heroHighlights.map((item) => (
                  <div key={item.label} className="rounded-2xl bg-gradient-to-r from-emerald-50 to-teal-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{item.label}</p>
                    <h3 className="mt-2 text-lg font-semibold text-slate-900">{item.value}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-3xl border border-emerald-100 bg-white/90 p-5 shadow-sm">
                <LineChart className="h-6 w-6 text-emerald-600" />
                <h3 className="mt-4 text-lg font-semibold">Progress that informs action</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">The platform turns learning activity into clearer decisions for students, teachers, and parents.</p>
              </div>
              <div className="rounded-3xl border border-emerald-100 bg-white/90 p-5 shadow-sm">
                <MessageSquare className="h-6 w-6 text-emerald-600" />
                <h3 className="mt-4 text-lg font-semibold">Support that stays reachable</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">Visitors can move directly from the landing page into signup, login, policies, or support contact.</p>
              </div>
            </div>
          </div>
        </section>

        <section id="about" className="py-12">
          <SectionTitle
            eyebrow="About"
            title="EduMate is a complete academic workflow platform, not just a basic learning tool."
            description="The platform is designed to support the full flow of learning and academic coordination. It helps students learn better, gives teachers stronger working tools, and gives parents and institutions more useful visibility into progress."
          />
          <div className="mt-10 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="rounded-[32px] border border-emerald-100 bg-white p-8 shadow-sm">
              <h3 className="text-2xl font-semibold text-slate-900">What the platform does in real terms</h3>
              <div className="mt-5 space-y-5 text-sm leading-8 text-slate-600 sm:text-base">
                <p>
                  EduMate is built for the real rhythm of study and teaching. A student may begin with a doubt, continue into guided study content, move
                  into quizzes, and then review performance. A teacher may create content, build assessments, upload material, and monitor how students
                  are engaging. A parent may want a simpler view of progress and activity. The platform supports all of these use cases inside one connected system.
                </p>
                <p>
                  That connected design matters because education often becomes fragmented very quickly. Content may be stored in one place, tests in
                  another, doubts in another, and progress discussion somewhere else. EduMate reduces that fragmentation by keeping core academic actions
                  together so users spend less effort managing tools and more effort improving learning outcomes.
                </p>
                <p>
                  The AI capability is important, but the real strength of the product is the way it is structured around practical use. EduMate is not
                  built around a single flashy feature. It is a dependable academic workspace where explanation, practice, revision, reporting, and visibility
                  reinforce one another.
                </p>
              </div>
            </div>
            <div className="grid auto-rows-fr gap-5 sm:grid-cols-2">
              {aboutCards.map((item) => {
                const Icon = item.icon;
                return (
                  <article key={item.title} className="flex h-full flex-col rounded-[28px] border border-emerald-100 bg-white p-6 shadow-sm">
                    <div className="inline-flex rounded-2xl bg-emerald-100 p-3">
                      <Icon className="h-6 w-6 text-emerald-700" />
                    </div>
                    <h3 className="mt-5 text-xl font-semibold text-slate-900">{item.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-slate-600">{item.description}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section id="features" className="py-12">
          <SectionTitle
            eyebrow="Features"
            title="The application features explained through real product use."
            description="Each section below reflects an actual part of the EduMate experience. Together these features create a stronger academic system for self-study, classroom support, and parental visibility."
          />
          <div className="mt-10 grid gap-5 lg:grid-cols-2">
            {featureCards.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="flex h-full flex-col rounded-[30px] border border-emerald-100 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
                  <div className="flex items-start gap-4">
                    <div className="rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-600 p-3 text-white">
                      <Icon className="h-6 w-6" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-semibold text-slate-900">{item.title}</h3>
                      <p className="mt-3 text-sm leading-7 text-slate-600">{item.description}</p>
                    </div>
                  </div>
                  <div className="mt-5 grid flex-1 gap-3">
                    {item.details.map((detail) => (
                      <div key={detail} className="flex items-start gap-3 rounded-2xl bg-emerald-50/70 px-4 py-3">
                        <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-600" />
                        <p className="text-sm leading-6 text-slate-600">{detail}</p>
                      </div>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section id="workflow" className="py-12">
          <SectionTitle
            eyebrow="How It Works"
            title="A role-based workflow that stays simple even as the platform does more."
            description="EduMate is designed so different users can enter the system for different reasons while still participating in one connected academic flow."
          />
          <div className="mt-10 grid gap-5 lg:grid-cols-4">
            {workflowSteps.map((item) => (
              <article key={item.step} className="flex h-full flex-col rounded-[28px] border border-emerald-100 bg-white p-6 shadow-sm">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-r from-emerald-500 to-teal-600 text-lg font-bold text-white">
                  {item.step}
                </div>
                <h3 className="mt-5 text-xl font-semibold text-slate-900">{item.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{item.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="community" className="py-12">
          <SectionTitle
            eyebrow="Who It Helps"
            title="Different users get different value, but the system stays connected."
            description="EduMate is designed to serve the people who actually participate in learning every day. Each role has its own needs, and the platform reflects that without losing continuity across the wider academic journey."
          />
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {audienceCards.map((card) => {
              const Icon = card.icon;
              return (
                <article key={card.title} className="flex h-full flex-col rounded-[28px] border border-emerald-100 bg-white p-6 shadow-sm">
                  <Icon className="h-8 w-8 text-emerald-700" />
                  <h3 className="mt-5 text-xl font-semibold text-slate-900">{card.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-600">{card.description}</p>
                  <div className="mt-5 space-y-3">
                    {card.points.map((point) => (
                      <div key={point} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
                        {point}
                      </div>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section id="modules" className="py-12">
          <SectionTitle
            eyebrow="Platform Modules"
            title="The platform covers the major academic needs of each user type."
            description="These summary cards give a quick product-level view of what is available inside EduMate today."
          />
          <div className="mt-10 grid gap-5 lg:grid-cols-3">
            {platformModules.map((item) => (
              <article key={item.title} className="flex h-full flex-col rounded-[28px] border border-emerald-100 bg-white p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-slate-900">{item.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{item.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="py-12">
          <div className="rounded-[32px] border border-emerald-100 bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-10 text-white shadow-lg sm:px-10">
            <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-100">Why EduMate works</p>
                <h2 className="mt-4 text-3xl font-bold">Clarity for students, efficiency for teachers, visibility for families.</h2>
                <p className="mt-4 max-w-3xl text-base leading-8 text-emerald-50">
                  EduMate brings together the actions that matter most in academic support: asking, learning, practicing, reviewing, tracking, and
                  following up. That connected structure is what gives the platform long-term value beyond a single feature or one-time interaction.
                </p>
              </div>
              <div className="rounded-[28px] bg-white/10 p-6 backdrop-blur-sm">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-100">Included across the platform</p>
                <ul className="mt-4 space-y-3 text-sm leading-7 text-emerald-50">
                  <li>AI tutor support and structured question answering</li>
                  <li>Study content, quizzes, custom quizzes, and uploads</li>
                  <li>Notes, PDFs, progress visibility, and learning tools</li>
                  <li>Role-based access for students, teachers, parents, and admins</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section id="contact" className="py-12">
          <SectionTitle
            eyebrow="Contact"
            title="Reach out for onboarding, support, partnerships, or implementation questions."
            description="The contact form below sends your request through the backend mail flow using the configured Google SMTP environment variables, so your support process can stay centralized and reliable."
          />
          <div className="mt-10 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-[28px] border border-emerald-100 bg-white p-6 shadow-sm">
              <h3 className="text-xl font-semibold text-slate-900">Contact information</h3>
              <div className="mt-6 space-y-5 text-sm leading-7 text-slate-600">
                <div className="flex items-start gap-3">
                  <Building2 className="mt-1 h-5 w-5 text-emerald-600" />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Organization</p>
                    <p className="mt-1">Patliputra Educational Toys</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <MapPin className="mt-1 h-5 w-5 text-emerald-600" />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Registered Office</p>
                    <p className="mt-1">Shivpur, Tikiya Toli, Musallahpur Hatt, Patna, Bihar, India</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Mail className="mt-1 h-5 w-5 text-emerald-600" />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Use Cases</p>
                    <p className="mt-1">Onboarding, platform support, institution inquiries, product questions, partnership discussions, and policy-related communication.</p>
                  </div>
                </div>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="rounded-[28px] border border-emerald-100 bg-white p-6 shadow-sm">
              {submissionState.message && (
                <div
                  className={`mb-4 rounded-2xl border px-4 py-3 text-sm ${
                    submissionState.type === "success"
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-red-200 bg-red-50 text-red-700"
                  }`}
                >
                  {submissionState.message}
                </div>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <input
                    type="text"
                    value={formData.full_name}
                    onChange={(event) => handleChange("full_name", event.target.value)}
                    placeholder="Full Name"
                    className={getInputClassName("full_name")}
                    required
                  />
                  {fieldErrors.full_name && <p className="mt-1 text-xs text-red-600">{fieldErrors.full_name}</p>}
                </div>
                <div>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(event) => handleChange("email", event.target.value)}
                    placeholder="Email Address"
                    className={getInputClassName("email")}
                    required
                  />
                  {fieldErrors.email && <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>}
                </div>
                <div>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(event) => handleChange("phone", event.target.value)}
                    placeholder="Phone Number"
                    className={getInputClassName("phone")}
                  />
                  {fieldErrors.phone && <p className="mt-1 text-xs text-red-600">{fieldErrors.phone}</p>}
                </div>
                <div>
                  <select
                    value={formData.role}
                    onChange={(event) => handleChange("role", event.target.value)}
                    className={getInputClassName("role")}
                  >
                    <option value="student">Student</option>
                    <option value="teacher">Teacher</option>
                    <option value="parent">Parent</option>
                    <option value="institution">Institution</option>
                  </select>
                  {fieldErrors.role && <p className="mt-1 text-xs text-red-600">{fieldErrors.role}</p>}
                </div>
              </div>
              <div className="mt-4 grid gap-4">
                <div>
                  <input
                    type="text"
                    value={formData.institution}
                    onChange={(event) => handleChange("institution", event.target.value)}
                    placeholder="School, coaching, or organization"
                    className={getInputClassName("institution")}
                  />
                  {fieldErrors.institution && <p className="mt-1 text-xs text-red-600">{fieldErrors.institution}</p>}
                </div>
                <div>
                  <input
                    type="text"
                    value={formData.subject}
                    onChange={(event) => handleChange("subject", event.target.value)}
                    placeholder="Subject or reason for contact"
                    className={getInputClassName("subject")}
                    required
                  />
                  {fieldErrors.subject && <p className="mt-1 text-xs text-red-600">{fieldErrors.subject}</p>}
                </div>
                <div>
                  <textarea
                    value={formData.message}
                    onChange={(event) => handleChange("message", event.target.value)}
                    placeholder="Tell us what you need, what kind of support you are looking for, or what questions you want answered."
                    rows={6}
                    minLength={3}
                    className={`w-full rounded-3xl border px-4 py-3 text-sm focus:outline-none focus:ring-2 ${
                      fieldErrors.message
                        ? "border-red-300 focus:border-red-400 focus:ring-red-200"
                        : "border-slate-200 focus:border-emerald-400 focus:ring-emerald-200"
                    }`}
                    required
                  />
                  {fieldErrors.message && <p className="mt-1 text-xs text-red-600">{fieldErrors.message}</p>}
                  {!fieldErrors.message && <p className="mt-1 text-xs text-slate-500">Please add a short message so we can help quickly.</p>}
                </div>
              </div>
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                <button type="submit" disabled={isSubmitting} className="rounded-full bg-gradient-to-r from-emerald-500 to-teal-600 px-6 py-3 text-sm font-semibold text-white transition hover:from-emerald-600 hover:to-teal-700 disabled:cursor-not-allowed disabled:opacity-70">
                  {isSubmitting ? "Sending..." : "Send Message"}
                </button>
              </div>
            </form>
          </div>
        </section>
      </main>

      <footer className="border-t border-emerald-100 bg-white/90">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1.2fr_0.8fr_0.8fr_0.8fr_0.8fr]">
          <div>
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 overflow-hidden rounded-xl ring-1 ring-emerald-200">
                <img src={edumatelogo} alt="EduMate" className="h-full w-full object-cover" />
              </div>
              <div>
                <p className="text-sm font-bold text-emerald-700">EduMate</p>
                <p className="text-xs text-slate-500">AI-powered learning platform</p>
              </div>
            </div>
            <p className="mt-4 max-w-sm text-sm leading-7 text-slate-600">
              EduMate is an AI-powered academic platform that brings study support, assessment, revision, progress visibility, and user coordination into one connected experience.
            </p>
          </div>

          {footerColumns.map((column) => (
            <div key={column.title}>
              <h3 className="text-sm font-bold uppercase tracking-[0.18em] text-slate-900">{column.title}</h3>
              <div className="mt-4 space-y-3 text-sm">
                {column.links.map((link) =>
                  link.type === "scroll" ? (
                    <button key={link.label} onClick={() => scrollTo(link.href)} className="block text-left text-slate-600 transition hover:text-emerald-700">
                      {link.label}
                    </button>
                  ) : (
                    <Link key={link.label} to={link.href} className="block text-slate-600 transition hover:text-emerald-700">
                      {link.label}
                    </Link>
                  )
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="border-t border-emerald-100 px-4 py-4 text-center text-sm text-slate-500 sm:px-6">
          Copyright {new Date().getFullYear()} EduMate by Patliputra Educational Toys. All rights reserved.
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
