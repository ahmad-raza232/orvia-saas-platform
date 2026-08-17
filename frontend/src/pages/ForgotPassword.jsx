import { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'react-toastify';
import { CircleCheck } from 'lucide-react';
import AuthShell from '../components/layout/AuthShell';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

import { API_URL } from '../config/api';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Email is required');
      return;
    }
    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/auth/forgot-password`, {
        email: email.trim(),
      });
      if (response.data.success) {
        setEmailSent(true);
        toast.success('Password reset instructions sent to your email!');
      }
    } catch (err) {
      console.error('Forgot password error:', err);
      const message = err.response?.data?.message || 'Failed to send reset email. Please try again.';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  if (emailSent) {
    return (
      <div className="flex min-h-[calc(100vh-4.25rem)] items-center justify-center bg-canvas px-4 py-16">
        <Card className="w-full max-w-md p-8 text-center">
          <CircleCheck className="mx-auto h-12 w-12 text-success" />
          <h1 className="mt-4 font-display text-3xl text-ink">Check your email</h1>
          <p className="mt-2 text-sm text-ink-secondary">We sent reset instructions to</p>
          <p className="mt-1 font-semibold text-olive">{email}</p>
          <div className="mt-6 space-y-3">
            <Button variant="outline" className="w-full" onClick={() => setEmailSent(false)}>
              Try another email
            </Button>
            <Button to="/login" className="w-full">
              Back to login
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <AuthShell title="Forgot password?" subtitle="Enter your email and we’ll send reset instructions.">
      <form onSubmit={handleSubmit} className="space-y-5">
        <Input
          label="Email address"
          type="email"
          name="email"
          placeholder="example@gmail.com"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            setError('');
          }}
          error={error}
        />
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Sending...' : 'Send reset link'}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm">
        <Link to="/login" className="font-medium text-olive hover:underline">
          Back to login
        </Link>
      </p>
    </AuthShell>
  );
};

export default ForgotPassword;
