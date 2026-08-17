import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AuthShell from '../components/layout/AuthShell';
import Input from '../components/ui/Input';
import Textarea from '../components/ui/Textarea';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

const emptyOptional = {
  business_name: '',
  business_type: '',
  business_address: '',
  business_registration_number: '',
  bank_name: '',
  account_title: '',
  account_number: '',
  iban: '',
};

/**
 * Softorica registration. Only API-supported fields are submitted to the tenant API.
 * Business/bank blocks are UI-only until a future module persists them.
 */
const Register = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    address: '',
    password: '',
    confirmPassword: '',
    ...emptyOptional,
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
    // Only Modules 1–11 auth fields are sent. Optional business/bank fields stay client-side.
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
      wide
      title="Create account"
      subtitle="Join Softorica for fast and secure deliveries across your operations."
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
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-olive">
            Personal information
          </h2>
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
          <Textarea
            label="Address"
            name="address"
            rows={2}
            value={formData.address}
            onChange={handleChange}
            hint="Optional — not stored by the current Softorica auth API"
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

        <Card className="space-y-4 border-dashed bg-muted/40 p-4">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-muted">
              Business information (optional)
            </h2>
            <p className="mt-1 text-xs text-ink-muted">
              Collected for UI completeness. Not submitted until Softorica adds account profile
              fields.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Business name"
              name="business_name"
              value={formData.business_name}
              onChange={handleChange}
            />
            <Input
              label="Business type"
              name="business_type"
              value={formData.business_type}
              onChange={handleChange}
            />
            <Input
              label="Business address"
              name="business_address"
              className="sm:col-span-2"
              value={formData.business_address}
              onChange={handleChange}
            />
            <Input
              label="Business registration number"
              name="business_registration_number"
              className="sm:col-span-2"
              value={formData.business_registration_number}
              onChange={handleChange}
            />
          </div>
        </Card>

        <Card className="space-y-4 border-dashed bg-muted/40 p-4">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-ink-muted">
              Bank information (optional)
            </h2>
            <p className="mt-1 text-xs text-ink-muted">
              Not submitted to the Softorica API. Do not enter live credentials you are not ready
              to store.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Bank name"
              name="bank_name"
              value={formData.bank_name}
              onChange={handleChange}
            />
            <Input
              label="Account title"
              name="account_title"
              value={formData.account_title}
              onChange={handleChange}
            />
            <Input
              label="Account number"
              name="account_number"
              value={formData.account_number}
              onChange={handleChange}
              autoComplete="off"
            />
            <Input
              label="IBAN"
              name="iban"
              value={formData.iban}
              onChange={handleChange}
              autoComplete="off"
            />
          </div>
        </Card>

        <p className="rounded-md bg-olive-light/60 px-3 py-2 text-xs text-ink-secondary">
          Softorica protects account credentials with hashed passwords and organization-scoped
          access. We never store plaintext passwords.
        </p>

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Creating account…' : 'Create Account'}
        </Button>
      </form>
    </AuthShell>
  );
};

export default Register;
