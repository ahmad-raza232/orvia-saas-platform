import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AuthShell from '../components/layout/AuthShell';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const from = location.state?.from?.pathname || '/app';
  const showDemoHint = import.meta.env.DEV;

  const handleChange = (event) => {
    setFormData({ ...formData, [event.target.name]: event.target.value });
    if (errors[event.target.name]) {
      setErrors({ ...errors, [event.target.name]: '' });
    }
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Enter a valid email';
    }
    if (!formData.password.trim()) {
      newErrors.password = 'Password is required';
    }
    return newErrors;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const newErrors = validate();
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setLoading(true);
    const result = await login(formData);
    setLoading(false);

    if (result.success) {
      let dest = '/app';
      if (!result.organizationId) dest = '/app/onboarding';
      else if (from.startsWith('/app')) dest = from;
      navigate(dest, { replace: true });
    }
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your ORVIA logistics workspace."
      footer={
        <>
          <p className="mt-6 text-center text-sm text-ink-secondary">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="font-semibold text-olive hover:underline">
              Get Started
            </Link>
          </p>
          <p className="mt-3 text-center text-xs text-ink-muted">
            Looking for public tracking?{' '}
            <Link to="/track" className="font-semibold text-olive hover:underline">
              Track with an ORVIA ID
            </Link>
          </p>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <Input
          label="Email address"
          type="email"
          name="email"
          placeholder="you@company.com"
          value={formData.email}
          onChange={handleChange}
          error={errors.email}
          autoComplete="email"
        />
        <Input
          label="Password"
          type="password"
          name="password"
          placeholder="Enter your password"
          value={formData.password}
          onChange={handleChange}
          error={errors.password}
          autoComplete="current-password"
        />
        {showDemoHint && (
          <p className="rounded-md bg-muted px-3 py-2 text-xs text-ink-secondary">
            Local demo: enable <span className="font-mono">DEMO_SEED_ENABLED</span> on the API,
            then sign in with the email from your backend <span className="font-mono">.env</span>.
            Accounts persist in PostgreSQL across restarts.
          </p>
        )}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </AuthShell>
  );
};

export default Login;
