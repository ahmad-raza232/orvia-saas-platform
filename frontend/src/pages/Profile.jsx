import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';
import axios from 'axios';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import Select from '../components/ui/Select';
import Button from '../components/ui/Button';

import { API_URL } from '../config/api';

const Profile = () => {
  const { user, logout, updateUser } = useAuth();
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    address: '',
    businessName: '',
    businessType: '',
    businessAddress: '',
    businessRegNo: '',
    bankName: '',
    accountTitle: '',
    accountNumber: '',
    iban: '',
  });

  const businessTypes = [
    'Sole Proprietor',
    'Private Limited',
    'Partnership',
    'E-commerce Store',
    'Retail Shop',
    'Wholesale',
    'Other',
  ];

  const pakistaniBanks = [
    'HBL - Habib Bank Limited',
    'UBL - United Bank Limited',
    'MCB - Muslim Commercial Bank',
    'NBP - National Bank of Pakistan',
    'ABL - Allied Bank Limited',
    'Meezan Bank',
    'Bank Alfalah',
    'Faysal Bank',
    'Standard Chartered Bank',
    'JS Bank',
    'Silk Bank',
    'Bank Al Habib',
    'Soneri Bank',
    'Askari Bank',
    'Other',
  ];

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = localStorage.getItem('goburq_token');
        const response = await axios.get(`${API_URL}/auth/profile/full`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.data.success && response.data.user) {
          const userData = response.data.user;
          setFormData({
            name: userData.name || '',
            email: userData.email || '',
            phone: userData.phone || '',
            address: userData.address || '',
            businessName: userData.business_name || '',
            businessType: userData.business_type || '',
            businessAddress: userData.business_address || '',
            businessRegNo: userData.business_reg_no || '',
            bankName: userData.bank_name || '',
            accountTitle: userData.account_title || '',
            accountNumber: userData.account_number || '',
            iban: userData.iban || '',
          });
        }
      } catch (error) {
        console.error('Fetch profile error:', error);
        if (error.response?.status === 401) {
          toast.error('Session expired. Please login again.');
          logout();
          navigate('/login');
          return;
        }
        toast.error('Failed to load profile data');
      }
    };

    fetchProfile();
  }, []);

  const handleChange = (event) => {
    setFormData({ ...formData, [event.target.name]: event.target.value });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem('goburq_token');
      const response = await axios.put(
        `${API_URL}/users/profile`,
        {
          name: formData.name,
          phone: formData.phone,
          address: formData.address,
          businessInfo: {
            businessName: formData.businessName,
            businessType: formData.businessType,
            businessAddress: formData.businessAddress,
            businessRegNo: formData.businessRegNo,
          },
          bankInfo: {
            bankName: formData.bankName,
            accountTitle: formData.accountTitle,
            accountNumber: formData.accountNumber,
            iban: formData.iban,
          },
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.data.success) {
        toast.success('Profile updated successfully!');
        updateUser(response.data.user || response.data.data?.user);
        setIsEditing(false);
      }
    } catch (error) {
      console.error('Profile update error:', error);
      if (error.response?.status === 401) {
        toast.error('Session expired. Please login again.');
        logout();
        navigate('/login');
        return;
      }
      toast.error(error.response?.data?.message || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (user) {
      setFormData({
        name: user.name || '',
        email: user.email || '',
        phone: user.phone || '',
        address: user.address || '',
        businessName: user.businessInfo?.businessName || '',
        businessType: user.businessInfo?.businessType || '',
        businessAddress: user.businessInfo?.businessAddress || '',
        businessRegNo: user.businessInfo?.businessRegNo || '',
        bankName: user.bankInfo?.bankName || '',
        accountTitle: user.bankInfo?.accountTitle || '',
        accountNumber: user.bankInfo?.accountNumber || '',
        iban: user.bankInfo?.iban || '',
      });
    }
    setIsEditing(false);
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-olive">Account</p>
          <h1 className="mt-2 font-display text-h1 text-ink">My profile</h1>
          <p className="text-ink-secondary">Manage your personal, business, and settlement details.</p>
        </div>
        {!isEditing ? (
          <Button onClick={() => setIsEditing(true)}>Edit profile</Button>
        ) : (
          <div className="flex gap-3">
            <Button variant="outline" onClick={handleCancel}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? 'Saving...' : 'Save changes'}
            </Button>
          </div>
        )}
      </div>

      <Card className="p-6 sm:p-8">
        <h2 className="mb-5 font-display text-xl">Personal information</h2>
        <div className="grid gap-5 md:grid-cols-2">
          <Input label="Full name" name="name" value={formData.name} onChange={handleChange} disabled={!isEditing} />
          <Input label="Email address" name="email" type="email" value={formData.email} disabled hint="Email cannot be changed" />
          <Input label="Phone number" name="phone" type="tel" value={formData.phone} onChange={handleChange} disabled={!isEditing} />
          <Input label="Address" name="address" value={formData.address} onChange={handleChange} disabled={!isEditing} />
        </div>
      </Card>

      <Card className="p-6 sm:p-8">
        <h2 className="mb-5 font-display text-xl">Business information</h2>
        <div className="grid gap-5 md:grid-cols-2">
          <Input label="Business name" name="businessName" value={formData.businessName} onChange={handleChange} disabled={!isEditing} placeholder="Not provided" />
          <Select label="Business type" name="businessType" value={formData.businessType} onChange={handleChange} disabled={!isEditing}>
            <option value="">Select type</option>
            {businessTypes.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </Select>
          <div className="md:col-span-2">
            <Input label="Business address" name="businessAddress" value={formData.businessAddress} onChange={handleChange} disabled={!isEditing} placeholder="Not provided" />
          </div>
          <div className="md:col-span-2">
            <Input label="Business registration number" name="businessRegNo" value={formData.businessRegNo} onChange={handleChange} disabled={!isEditing} placeholder="Not provided" />
          </div>
        </div>
      </Card>

      <Card className="p-6 sm:p-8">
        <h2 className="mb-5 font-display text-xl">Bank information</h2>
        <div className="grid gap-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <Select label="Bank name" name="bankName" value={formData.bankName} onChange={handleChange} disabled={!isEditing}>
              <option value="">Select bank</option>
              {pakistaniBanks.map((bank) => (
                <option key={bank} value={bank}>{bank}</option>
              ))}
            </Select>
          </div>
          <Input label="Account title" name="accountTitle" value={formData.accountTitle} onChange={handleChange} disabled={!isEditing} placeholder="Not provided" />
          <Input label="Account number" name="accountNumber" value={formData.accountNumber} onChange={handleChange} disabled={!isEditing} placeholder="Not provided" />
          <div className="md:col-span-2">
            <Input label="IBAN" name="iban" value={formData.iban} onChange={handleChange} disabled={!isEditing} placeholder="PK## XXXX #### #### #### ####" />
          </div>
        </div>
        <p className="mt-5 rounded-md bg-peach-soft px-4 py-3 text-sm text-ink-secondary">
          Bank information is used only for COD settlements and refunds.
        </p>
      </Card>
    </div>
  );
};

export default Profile;
