import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      brand: "RealtorAgentAI",
      nav: {
        dashboard: "Dashboard",
        documents: "Documents",
        contracts: "Contracts",
        review: "Review",
        signatures: "Signatures",
        admin: "Admin",
        logout: "Logout",
        welcome: "Welcome, {{name}}",
      },
      login: {
        title: "RealtorAgentAI",
        subtitle: "Multi-Agent Real Estate Contract Platform",
        signIn: "Sign in to your account",
        description: "Enter your email and password to access your dashboard",
        email: "Email address",
        password: "Password",
        submit: "Sign in",
        submitting: "Signing in...",
        demo: "Demo credentials: admin@example.com / password",
        success: {
          title: "Success",
          message: "You have been logged in successfully.",
        },
        error: {
          title: "Error",
          message: "Login failed. Please try again.",
        },
      },
      dashboard: {
        title: "Dashboard",
        subtitle: "Overview of your real estate contracts and activities",
        widgets: {
          myDeals: "My Deals",
          pending: "Pending Signatures",
          compliance: "Compliance Alerts",
          uploads: "Recent Uploads",
          documentIntake: {
            title: "Document Intake",
            description: "Upload and process real estate documents",
            action: "Upload Documents",
          },
          contractGenerator: {
            title: "Contract Generator",
            description: "Generate contracts from templates",
            action: "Create Contract",
          },
          signatureTracker: {
            title: "Signature Tracker",
            description: "Track multi-party signatures",
            action: "View Signatures",
          },
        },
      },
    },
  },
  vi: {
    translation: {
      brand: "RealtorAgentAI",
      nav: {
        dashboard: "Bảng điều khiển",
        documents: "Tài liệu",
        contracts: "Hợp đồng",
        review: "Xem lại",
        signatures: "Chữ ký",
        admin: "Quản trị",
        logout: "Đăng xuất",
        welcome: "Xin chào, {{name}}",
      },
      login: {
        title: "RealtorAgentAI",
        subtitle: "Nền tảng hợp đồng bất động sản đa tác nhân",
        signIn: "Đăng nhập vào tài khoản",
        description: "Nhập email và mật khẩu để truy cập bảng điều khiển",
        email: "Địa chỉ email",
        password: "Mật khẩu",
        submit: "Đăng nhập",
        submitting: "Đang đăng nhập...",
        demo: "Tài khoản demo: admin@example.com / password",
        success: {
          title: "Thành công",
          message: "Bạn đã đăng nhập thành công.",
        },
        error: {
          title: "Lỗi",
          message: "Đăng nhập thất bại. Vui lòng thử lại.",
        },
      },
      dashboard: {
        title: "Bảng điều khiển",
        subtitle: "Tổng quan về hợp đồng và hoạt động bất động sản của bạn",
        widgets: {
          myDeals: "Giao dịch của tôi",
          pending: "Chữ ký chờ",
          compliance: "Cảnh báo tuân thủ",
          uploads: "Tải lên gần đây",
          documentIntake: {
            title: "Nhập tài liệu",
            description: "Tải lên và xử lý tài liệu bất động sản",
            action: "Tải lên tài liệu",
          },
          contractGenerator: {
            title: "Trình tạo hợp đồng",
            description: "Tạo hợp đồng từ mẫu",
            action: "Tạo hợp đồng",
          },
          signatureTracker: {
            title: "Trình theo dõi chữ ký",
            description: "Theo dõi chữ ký đa bên",
            action: "Xem chữ ký",
          },
        },
      },
    },
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
