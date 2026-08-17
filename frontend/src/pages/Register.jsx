import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AuthShell from '../components/layout/AuthShell';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';

const Register = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const handleChange = (event) => {
    setFormData({ ...formData, [event.target.name]: event.target.value });
    if (errors[event.target.name]) {
      setErrors({ ...errors, [event.target.name]: '' });
    }
  };

  const validate = () => {
    const next = {};
    if (!formData.first_name.trim()) next.first_name = 'First name is required';
    if (!formData.last_name.trim()) next.last_name = 'Last name is required';
    if (!formData.email.trim()) next.email = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(formData.email)) next.email = 'Enter a valid email';
    if (!formData.password) next.password = 'Password is required';
    else if (formData.password.length < 10) {
      next.password = 'Password must be at least 10 characters';
    }
    if (formData.password !== formData.confirmPassword) {
      next.confirmPassword = 'Passwords do not match';
    }
    return next;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const next = validate();
    if (Object.keys(next).length) {
      setErrors(next);
      return;
    }
    setLoading(true);
    const result = await register({
      first_name: formData.first_name.trim(),
      last_name: formData.last_name.trim(),
      email: formData.email.trim(),
      phone: formData.phone.trim() || null,
      password: formData.password,
      name: `${formData.first_name} ${formData.last_name}`.trim(),
    });
    setLoading(false);
    if (result.success) {
      navigate(result.organizationId ? '/app' : '/app/onboarding', { replace: true });
    } else if (result.fields) {
      setErrors(result.fields);
    }
  };

  return (
    <AuthShell
      title="Create your ORVIA account"
      subtitle="Join Softorica’s logistics SaaS to manage shipments, riders, and tracking."
      footer={
        <p className="mt-6 text-center text-sm text-ink-secondary">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-olive hover:underline">
            Login
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-6" autoComplete="off">
        <section className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="First name"
              name="first_name"
              value={formData.first_name}
              onChange={handleChange}
              error={errors.first_name}
              required
              autoComplete="given-name"
            />
            <Input
              label="Last name"
              name="last_name"
              value={formData.last_name}
              onChange={handleChange}
              error={errors.last_name}
              required
              autoComplete="family-name"
            />
          </div>
          <Input
            label="Email address"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            error={errors.email}
            required
            autoComplete="email"
          />
          <Input
            label="Phone number"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            error={errors.phone}
            hint="Optional"
            autoComplete="tel"
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Password"
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              error={errors.password}
              hint="At least 10 characters"
              required
              autoComplete="new-password"
            />
            <Input
              label="Confirm password"
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              error={errors.confirmPassword}
              required
              autoComplete="new-password"
            />
          </div>
        </section>

        <p className="rounded-md bg-olive-light/60 px-3 py-2 text-xs text-ink-secondary">
          After you register, create an organization to start booking ORVIA shipments.
          Passwords are hashed. Accounts live in PostgreSQL and survive application restarts.
        </p>

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Creating account…' : 'Get Started'}
        </Button>
      </form>
    </AuthShell>
  );
};

export default Register;
