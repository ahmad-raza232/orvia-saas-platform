import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'react-toastify';
import { CircleCheck, TriangleAlert } from 'lucide-react';
import AuthShell from '../components/layout/AuthShell';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import LoadingState from '../components/ui/LoadingState';

import { API_URL } from '../config/api';

const ResetPassword = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState('');
  const [formData, setFormData] = useState({ password: '', confirmPassword: '' });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [tokenValid, setTokenValid] = useState(null);
  const [resetSuccess, setResetSuccess] = useState(false);

  useEffect(() => {
    const resetToken = searchParams.get('token');
    if (!resetToken) {
      toast.error('Invalid reset link');
      navigate('/forgot-password');
      return;
    }
    setToken(resetToken);
    verifyToken(resetToken);
  }, [searchParams, navigate]);

  const verifyToken = async (resetToken) => {
    try {
      const response = await axios.post(`${API_URL}/auth/verify-reset-token`, {
        token: resetToken,
      });
      setTokenValid(Boolean(response.data.success));
    } catch (err) {
      console.error('Token Verification Error:', err);
      setTokenValid(false);
      toast.error('Reset link is invalid or expired');
    }
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData({ ...formData, [name]: value });
    if (errors[name]) setErrors({ ...errors, [name]: '' });
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.password) newErrors.password = 'Password is required';
    else if (formData.password.length < 6) newErrors.password = 'Password must be at least 6 characters';
    if (!formData.confirmPassword) newErrors.confirmPassword = 'Please confirm your password';
    else if (formData.password !== formData.confirmPassword) newErrors.confirmPassword = 'Passwords do not match';
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
    try {
      const response = await axios.post(`${API_URL}/auth/reset-password`, {
        token,
        password: formData.password,
      });
      if (response.data.success) {
        setResetSuccess(true);
        toast.success('Password reset successful!');
        setTimeout(() => navigate('/login'), 3000);
      }
    } catch (err) {
      console.error('Reset Password Error:', err);
      toast.error(err.response?.data?.message || 'Failed to reset password. Please try again.');
      if (err.response?.status === 400 || err.response?.status === 404) {
        setTokenValid(false);
      }
    } finally {
      setLoading(false);
    }
  };

  if (tokenValid === null) {
    return <LoadingState label="Verifying reset link..." />;
  }

  if (tokenValid === false) {
    return (
      <div className="flex min-h-[calc(100vh-4.25rem)] items-center justify-center bg-canvas px-4 py-16">
        <Card className="w-full max-w-md p-8 text-center">
          <TriangleAlert className="mx-auto h-12 w-12 text-danger" />
          <h1 className="mt-4 font-display text-3xl text-ink">Invalid or expired link</h1>
          <p className="mt-2 text-sm text-ink-secondary">
            This password reset link is invalid or has expired. Please request a new one.
          </p>
          <Button to="/forgot-password" className="mt-6 w-full">
            Request new link
          </Button>
        </Card>
      </div>
    );
  }

  if (resetSuccess) {
    return (
      <div className="flex min-h-[calc(100vh-4.25rem)] items-center justify-center bg-canvas px-4 py-16">
        <Card className="w-full max-w-md p-8 text-center">
          <CircleCheck className="mx-auto h-12 w-12 text-success" />
          <h1 className="mt-4 font-display text-3xl text-ink">Password reset successful</h1>
          <p className="mt-2 text-sm text-ink-secondary">You can now login with your new password.</p>
          <Button to="/login" className="mt-6 w-full">
            Go to login
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <AuthShell title="Reset your password" subtitle="Enter a new password below">
      <form onSubmit={handleSubmit} className="space-y-5">
        <Input
          label="New password"
          type="password"
          name="password"
          placeholder="Enter new password"
          value={formData.password}
          onChange={handleChange}
          error={errors.password}
        />
        <Input
          label="Confirm password"
          type="password"
          name="confirmPassword"
          placeholder="Confirm new password"
          value={formData.confirmPassword}
          onChange={handleChange}
          error={errors.confirmPassword}
        />
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Resetting password...' : 'Reset password'}
        </Button>
      </form>
    </AuthShell>
  );
};

export default ResetPassword;
