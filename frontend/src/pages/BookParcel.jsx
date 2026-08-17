import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';
import BookingReceipt from '../components/BookingReceipt';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import Select from '../components/ui/Select';
import Textarea from '../components/ui/Textarea';
import Button from '../components/ui/Button';
import LoadingState from '../components/ui/LoadingState';
import { formatMoney } from '../utils/format';
import { API_URL } from '../config/api';

const BookParcel = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [loadingPlans, setLoadingPlans] = useState(true);
  const [hasCustomPlan, setHasCustomPlan] = useState(false);

  const [formData, setFormData] = useState({
    senderName: '',
    senderPhone: '',
    senderAddress: '',
    senderCity: '',
    receiverName: '',
    receiverPhone: '',
    receiverAddress: '',
    receiverCity: '',
    packageType: 'standard',
    weight: '',
    dimensions: '',
    description: '',
    deliveryType: 'standard',
    pickupDate: '',
    paymentMethod: 'cod',
    codAmount: '',
    codChargeRate: '2',
  });

  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [calculatedPrice, setCalculatedPrice] = useState(null);
  const [showReceipt, setShowReceipt] = useState(false);
  const [bookingData, setBookingData] = useState(null);

  const cities = [
    'Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad',
    'Multan', 'Peshawar', 'Quetta', 'Sialkot', 'Gujranwala',
    'Hyderabad', 'Bahawalpur', 'Sargodha', 'Sukkur', 'Larkana',
  ];

  const packageTypes = [
    { value: 'document', label: 'Document' },
    { value: 'small', label: 'Small Package' },
    { value: 'medium', label: 'Medium Package' },
    { value: 'large', label: 'Large Package' },
    { value: 'fragile', label: 'Fragile' },
  ];

  useEffect(() => {
    fetchPlans();
  }, []);

  useEffect(() => {
    if (user) {
      setFormData((prev) => ({
        ...prev,
        senderName: user.name || '',
        senderPhone: user.phone || '',
        senderAddress: user.address || '',
      }));
    }
  }, [user]);

  useEffect(() => {
    calculatePrice();
  }, [selectedPlan, formData.senderCity, formData.receiverCity, formData.weight, formData.packageType, formData.deliveryType]);

  const fetchPlans = async () => {
    try {
      const token = localStorage.getItem('goburq_token');
      if (!token) {
        toast.error('Please login to book a parcel');
        navigate('/login');
        return;
      }

      const response = await fetch(`${API_URL}/plans/my-plan`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();

      if (data.success) {
        const planList = Array.isArray(data.data) ? data.data : [];
        setPlans(planList);
        setHasCustomPlan(Boolean(data.hasCustomPlan));
        if (planList.length > 0) setSelectedPlan(planList[0]);
        if (data.hasCustomPlan) {
          toast.success('You have a custom pricing plan assigned to you!', {
            autoClose: 4000,
            position: 'top-center',
          });
        }
      } else {
        toast.error('Failed to load your pricing plan');
      }
    } catch (error) {
      console.error('Failed to fetch plans:', error);
      toast.error('Failed to load pricing plan');
    } finally {
      setLoadingPlans(false);
    }
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const getCodServiceCharges = (amount, rate) => {
    const numericAmount = Number(amount);
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) return 0;
    if (rate === 'flat') return 100;
    const percent = rate === '3' ? 0.03 : 0.02;
    return Number((numericAmount * percent).toFixed(2));
  };

  const codServiceCharges =
    formData.paymentMethod === 'cod'
      ? getCodServiceCharges(formData.codAmount, formData.codChargeRate)
      : 0;

  const calculatePrice = async () => {
    if (!selectedPlan || !formData.senderCity || !formData.receiverCity || !formData.weight) {
      setCalculatedPrice(null);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/plans/calculate-price`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_id: selectedPlan.id,
          sender_city: formData.senderCity,
          receiver_city: formData.receiverCity,
          weight: parseFloat(formData.weight),
          package_type: formData.packageType,
          delivery_type: formData.deliveryType,
        }),
      });
      const data = await response.json();
      if (data.success) {
        setCalculatedPrice(data.data.breakdown);
      } else {
        toast.error(data.message);
        setCalculatedPrice(null);
      }
    } catch (error) {
      console.error('Price calculation error:', error);
      setCalculatedPrice(null);
    }
  };

  const validate = () => {
    const newErrors = {};
    if (!selectedPlan) newErrors.plan = 'Please select a pricing plan';
    if (!formData.senderName.trim()) newErrors.senderName = 'Sender name is required';
    if (!formData.senderPhone.trim()) newErrors.senderPhone = 'Sender phone is required';
    if (!formData.senderAddress.trim()) newErrors.senderAddress = 'Sender address is required';
    if (!formData.senderCity) newErrors.senderCity = 'Sender city is required';
    if (!formData.receiverName.trim()) newErrors.receiverName = 'Receiver name is required';
    if (!formData.receiverPhone.trim()) newErrors.receiverPhone = 'Receiver phone is required';
    if (!formData.receiverAddress.trim()) newErrors.receiverAddress = 'Receiver address is required';
    if (!formData.receiverCity) newErrors.receiverCity = 'Receiver city is required';
    if (!formData.weight || parseFloat(formData.weight) <= 0) newErrors.weight = 'Valid weight is required';
    if (!formData.pickupDate) newErrors.pickupDate = 'Pickup date is required';
    if (formData.paymentMethod === 'cod') {
      const numericAmount = Number(formData.codAmount);
      if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
        newErrors.codAmount = 'Valid COD amount is required';
      }
    }
    return newErrors;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const newErrors = validate();
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      toast.error('Please fill all required fields');
      return;
    }
    if (!calculatedPrice) {
      toast.error('Cannot calculate price. Please check all fields.');
      return;
    }

    const token = localStorage.getItem('goburq_token');
    if (!token) {
      toast.error('Please login to book a parcel');
      navigate('/login');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        plan_id: selectedPlan.id,
        senderName: formData.senderName,
        senderPhone: formData.senderPhone,
        senderAddress: formData.senderAddress,
        senderCity: formData.senderCity,
        receiverName: formData.receiverName,
        receiverPhone: formData.receiverPhone,
        receiverAddress: formData.receiverAddress,
        receiverCity: formData.receiverCity,
        packageType: formData.packageType,
        weight: parseFloat(formData.weight),
        dimensions: formData.dimensions,
        description: formData.description,
        deliveryType: formData.deliveryType,
        pickupDate: formData.pickupDate,
        price: calculatedPrice.total,
        paymentMethod: formData.paymentMethod,
      };

      if (formData.paymentMethod === 'cod') {
        payload.codAmount = Number(formData.codAmount);
        payload.cod_amount = payload.codAmount;
        payload.codChargeRate = formData.codChargeRate;
        payload.cod_charge_rate = payload.codChargeRate;
        payload.codServiceCharges = codServiceCharges;
        payload.cod_service_charges = payload.codServiceCharges;
      }

      const response = await fetch(`${API_URL}/bookings`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...payload }),
      });
      const data = await response.json();

      if (data.success) {
        toast.success(`Booking confirmed! Tracking ID: ${data.trackingId}`);

        if (import.meta.env.DEV && formData.paymentMethod === 'cod') {
          try {
            const verifyResponse = await fetch(`${API_URL}/bookings/my-bookings`, {
              headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
            });
            const verifyData = await verifyResponse.json();
            const list = verifyData?.bookings || verifyData?.data?.bookings || [];
            const persisted = list.find((booking) => {
              const tracking = booking?.tracking_id ?? booking?.trackingId ?? booking?.trackingID;
              return String(tracking) === String(data.trackingId);
            });
            if (!persisted) {
              toast.warning('Booking saved, but could not verify COD fields in DB response.');
            } else {
              const persistedCodAmount = persisted?.cod_amount ?? persisted?.codAmount;
              const persistedCodCharges = persisted?.cod_service_charges ?? persisted?.codServiceCharges;
              const expectedCodAmount = Number(formData.codAmount);
              const expectedCodCharges = Number(codServiceCharges);
              const codAmountOk =
                Number.isFinite(Number(persistedCodAmount)) &&
                Math.abs(Number(persistedCodAmount) - expectedCodAmount) < 0.01;
              const codChargesOk =
                Number.isFinite(Number(persistedCodCharges)) &&
                Math.abs(Number(persistedCodCharges) - expectedCodCharges) < 0.01;
              if (!codAmountOk || !codChargesOk) {
                toast.warning('COD fields mismatch in DB response. Backend should calculate and persist COD values.');
              }
            }
          } catch {
            toast.warning('Booking saved, but COD DB verification request failed.');
          }
        }

        setBookingData({
          ...formData,
          trackingId: data.trackingId,
          orderId: data.orderId || data.parcelId,
          price: calculatedPrice.total,
          codServiceCharges,
          planName: selectedPlan.name,
          bookingDate: new Date().toISOString(),
        });
        setShowReceipt(true);
      } else {
        toast.error(data.message || 'Failed to create booking');
      }
    } catch (error) {
      console.error('Booking Error:', error);
      toast.error('Failed to create booking. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCloseReceipt = () => {
    setShowReceipt(false);
    navigate('/user/bookings');
  };

  if (loadingPlans) {
    return <LoadingState label="Loading your pricing plan..." />;
  }

  if (plans.length === 0) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <h2 className="font-display text-2xl text-ink">No pricing plan assigned</h2>
        <p className="mt-3 text-ink-secondary">
          You don&apos;t have a pricing plan assigned yet. Please contact support to get a custom plan.
        </p>
        <div className="mt-6 space-y-3">
          <Button className="w-full" onClick={() => navigate('/')}>Go to home</Button>
          <Button href="tel:03263253256" variant="outline" className="w-full">
            Call support
          </Button>
        </div>
        <p className="mt-6 text-sm text-ink-muted">0326 3253256</p>
      </div>
    );
  }

  return (
    <>
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-olive">New shipment</p>
          <h1 className="mt-2 font-display text-h1 text-ink">Book your parcel</h1>
          <p className="text-ink-secondary">Sender, receiver, parcel, then confirmation.</p>
          {hasCustomPlan && selectedPlan && (
            <p className="mt-3 inline-flex rounded-full bg-peach-soft px-4 py-1.5 text-sm font-semibold text-olive">
              Custom plan: {selectedPlan.name}
            </p>
          )}
        </div>

        {plans.length > 1 && (
          <Card className="p-6 sm:p-8">
            <h2 className="font-display text-xl">Your pricing plans</h2>
            {errors.plan && <p className="mt-2 text-sm text-danger">{errors.plan}</p>}
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              {plans.map((plan) => (
                <button
                  type="button"
                  key={plan.id}
                  onClick={() => setSelectedPlan(plan)}
                  className={`rounded-lg border p-5 text-left transition-all ${
                    selectedPlan?.id === plan.id
                      ? 'border-olive bg-olive-light'
                      : 'border-line bg-surface hover:border-olive/40'
                  }`}
                >
                  <h3 className="font-display text-lg">{plan.name}</h3>
                  <p className="text-sm text-ink-muted">{plan.subtitle}</p>
                  <div className="mt-4 space-y-1 text-sm">
                    <p>Base: PKR {plan.base_rate}</p>
                    <p>Per KG: PKR {plan.per_kg_rate}</p>
                    <p>Per KM: PKR {plan.per_km_rate}</p>
                  </div>
                </button>
              ))}
            </div>
          </Card>
        )}

        {plans.length === 1 && selectedPlan && (
          <Card className="bg-peach-soft p-6">
            <h3 className="font-display text-xl">{selectedPlan.name}</h3>
            <p className="text-sm text-ink-secondary">{selectedPlan.subtitle}</p>
            <div className="mt-4 grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-ink-muted">Base rate</p>
                <p className="font-display text-lg text-olive">PKR {selectedPlan.base_rate}</p>
              </div>
              <div>
                <p className="text-xs text-ink-muted">Per KG</p>
                <p className="font-display text-lg text-olive">PKR {selectedPlan.per_kg_rate}</p>
              </div>
              <div>
                <p className="text-xs text-ink-muted">Per KM</p>
                <p className="font-display text-lg text-olive">PKR {selectedPlan.per_km_rate}</p>
              </div>
            </div>
          </Card>
        )}

        <Card className="p-6 sm:p-8">
          <h2 className="mb-5 font-display text-xl">1. Sender</h2>
          <div className="grid gap-5 md:grid-cols-2">
            <Input label="Full name" name="senderName" value={formData.senderName} onChange={handleChange} disabled={!!user} error={errors.senderName} required />
            <Input label="Phone number" type="tel" name="senderPhone" value={formData.senderPhone} onChange={handleChange} disabled={!!user} placeholder="+92 300 1234567" error={errors.senderPhone} required />
            <Select label="City" name="senderCity" value={formData.senderCity} onChange={handleChange} error={errors.senderCity} required>
              <option value="">Select city</option>
              {cities.map((city) => <option key={city} value={city}>{city}</option>)}
            </Select>
            <Input label="Full address" name="senderAddress" value={formData.senderAddress} onChange={handleChange} disabled={!!user} placeholder="Street, Area, Landmark" error={errors.senderAddress} required />
          </div>
        </Card>

        <Card className="p-6 sm:p-8">
          <h2 className="mb-5 font-display text-xl">2. Receiver</h2>
          <div className="grid gap-5 md:grid-cols-2">
            <Input label="Full name" name="receiverName" value={formData.receiverName} onChange={handleChange} error={errors.receiverName} required />
            <Input label="Phone number" type="tel" name="receiverPhone" value={formData.receiverPhone} onChange={handleChange} placeholder="+92 300 1234567" error={errors.receiverPhone} required />
            <Select label="City" name="receiverCity" value={formData.receiverCity} onChange={handleChange} error={errors.receiverCity} required>
              <option value="">Select city</option>
              {cities.map((city) => <option key={city} value={city}>{city}</option>)}
            </Select>
            <Input label="Full address" name="receiverAddress" value={formData.receiverAddress} onChange={handleChange} placeholder="Street, Area, Landmark" error={errors.receiverAddress} required />
          </div>
        </Card>

        <Card className="p-6 sm:p-8">
          <h2 className="mb-5 font-display text-xl">3. Parcel</h2>
          <div className="grid gap-5 md:grid-cols-2">
            <Select label="Package type" name="packageType" value={formData.packageType} onChange={handleChange} required>
              {packageTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </Select>
            <Input label="Weight (kg)" type="number" step="0.1" name="weight" value={formData.weight} onChange={handleChange} placeholder="e.g., 2.5" error={errors.weight} required />
            <Input label="Dimensions (optional)" name="dimensions" value={formData.dimensions} onChange={handleChange} placeholder="L x W x H (cm)" />
            <Select label="Delivery type" name="deliveryType" value={formData.deliveryType} onChange={handleChange} required>
              <option value="standard">Standard (2-3 days)</option>
              <option value="express">Express (1 day)</option>
            </Select>
            <div className="md:col-span-2">
              <Textarea label="Package description (optional)" name="description" value={formData.description} onChange={handleChange} rows={3} placeholder="What's inside the package?" />
            </div>
          </div>
        </Card>

        <Card className="p-6 sm:p-8">
          <h2 className="mb-5 font-display text-xl">4. Pickup and payment</h2>
          <div className="grid gap-5 md:grid-cols-2">
            <Input label="Pickup date" type="date" name="pickupDate" value={formData.pickupDate} onChange={handleChange} min={new Date().toISOString().split('T')[0]} error={errors.pickupDate} required />
            <Select label="Payment method" name="paymentMethod" value={formData.paymentMethod} onChange={handleChange} required>
              <option value="cod">Cash on Delivery (COD)</option>
              <option value="online">Online Payment</option>
              <option value="card">Credit/Debit Card</option>
            </Select>
          </div>

          {formData.paymentMethod === 'cod' && (
            <div className="mt-6 rounded-lg border border-olive/20 bg-peach-soft p-5">
              <p className="mb-4 font-semibold text-ink">Cash on delivery</p>
              <label className="mb-4 flex items-center gap-2 text-sm text-ink-secondary">
                <input type="checkbox" checked readOnly className="accent-olive" />
                This is a Cash on Delivery (COD) parcel
              </label>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="md:col-span-2">
                  <Input
                    label="COD amount to collect (Rs.)"
                    type="number"
                    name="codAmount"
                    value={formData.codAmount}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                    placeholder="Amount to collect from receiver"
                    error={errors.codAmount}
                    hint="This is the amount you'll collect from the receiver"
                    required
                  />
                </div>
                <Input
                  label="COD service charges (Rs.)"
                  value={formatMoney(codServiceCharges)}
                  readOnly
                  hint={formData.codChargeRate === 'flat' ? 'Flat Rs. 100' : `${formData.codChargeRate}% of COD amount`}
                />
              </div>
              <fieldset className="mt-5">
                <legend className="mb-2 text-sm font-semibold">COD charge rate</legend>
                <div className="space-y-2 text-sm">
                  {[
                    { value: '2', label: '2% (Standard)' },
                    { value: '3', label: '3% (Premium/Remote areas)' },
                    { value: 'flat', label: 'Flat Rs. 100' },
                  ].map((option) => (
                    <label key={option.value} className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="codChargeRate"
                        checked={formData.codChargeRate === option.value}
                        onChange={() => setFormData((prev) => ({ ...prev, codChargeRate: option.value }))}
                        className="accent-olive"
                      />
                      {option.label}
                    </label>
                  ))}
                </div>
              </fieldset>
            </div>
          )}
        </Card>

        {calculatedPrice && selectedPlan && (
          <Card className="bg-olive p-6 text-peach sm:p-8">
            <p className="text-sm text-peach/80">{selectedPlan.name} — estimated price</p>
            <p className="mt-2 font-display text-5xl">PKR {Number(calculatedPrice.total || 0).toLocaleString()}</p>
            <p className="mt-3 text-sm text-peach/80">
              ~{calculatedPrice.distance} km · {formData.weight} kg · {formData.senderCity} → {formData.receiverCity}
            </p>
          </Card>
        )}

        <div className="flex flex-col gap-3 sm:flex-row">
          <Button variant="outline" className="flex-1" onClick={() => navigate(-1)}>
            Cancel
          </Button>
          <Button
            className="flex-1"
            onClick={handleSubmit}
            disabled={loading || !calculatedPrice || !selectedPlan}
          >
            {loading ? 'Processing...' : 'Confirm booking'}
          </Button>
        </div>
      </div>

      {showReceipt && bookingData && (
        <BookingReceipt booking={bookingData} onClose={handleCloseReceipt} />
      )}
    </>
  );
};

export default BookParcel;
