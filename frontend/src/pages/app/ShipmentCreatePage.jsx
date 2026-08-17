import { useId, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext';
import { shipmentApi } from '../../services/tenantApi';
import { getApiErrorMessage, getValidationDetails } from '../../services/errors';
import {
  PAYMENT_COD,
  PAYMENT_PREPAID,
  buildCreateShipmentPayload,
  codCollectSummary,
  emptyParty,
  todayDateInputValue,
  validateShipmentCreateForm,
} from '../../utils/shipmentForm';
import SectionHeading from '../../components/ui/SectionHeading';
import Card from '../../components/ui/Card';
import Input from '../../components/ui/Input';
import Select from '../../components/ui/Select';
import Textarea from '../../components/ui/Textarea';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';

function PartyFields({ which, value, title, errors, onFieldChange, formId }) {
  const prefix = `${formId}-${which}`;
  const isSender = which === 'sender';

  return (
    <Card className="space-y-4 p-5">
      <h2 className="font-display text-lg text-ink">{title}</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Name"
          name={`${prefix}-name`}
          id={`${prefix}-name`}
          required
          autoComplete="off"
          data-party={which}
          value={value.name}
          error={errors[`${which}_name`]}
          onChange={(e) => onFieldChange(which, 'name', e.target.value)}
        />
        <Input
          label="Contact"
          name={`${prefix}-phone`}
          id={`${prefix}-phone`}
          required
          autoComplete="off"
          data-party={which}
          value={value.phone}
          error={errors[`${which}_phone`]}
          onChange={(e) => onFieldChange(which, 'phone', e.target.value)}
        />
        <div className="sm:col-span-2">
          <Input
            label={isSender ? 'Pickup Address' : 'Delivery Address'}
            name={`${prefix}-address`}
            id={`${prefix}-address`}
            required
            autoComplete="off"
            data-party={which}
            value={value.address}
            error={errors[`${which}_address`]}
            onChange={(e) => onFieldChange(which, 'address', e.target.value)}
          />
        </div>
        <Input
          label={isSender ? 'Origin / Return City' : 'Destination City'}
          name={`${prefix}-city`}
          id={`${prefix}-city`}
          required
          autoComplete="off"
          data-party={which}
          value={value.city}
          error={errors[`${which}_city`]}
          onChange={(e) => onFieldChange(which, 'city', e.target.value)}
        />
        <Input
          label="State / Province"
          name={`${prefix}-state`}
          id={`${prefix}-state`}
          autoComplete="off"
          data-party={which}
          value={value.state}
          hint="Optional"
          onChange={(e) => onFieldChange(which, 'state', e.target.value)}
        />
        <Input
          label="Country"
          name={`${prefix}-country`}
          id={`${prefix}-country`}
          required
          autoComplete="off"
          data-party={which}
          maxLength={2}
          value={value.country}
          onChange={(e) => onFieldChange(which, 'country', e.target.value.toUpperCase())}
        />
        <Input
          label="Postal code"
          name={`${prefix}-postal`}
          id={`${prefix}-postal`}
          autoComplete="off"
          data-party={which}
          value={value.postal_code}
          hint="Optional"
          onChange={(e) => onFieldChange(which, 'postal_code', e.target.value)}
        />
        <Input
          label="Email"
          type="email"
          name={`${prefix}-email`}
          id={`${prefix}-email`}
          autoComplete="off"
          data-party={which}
          value={value.email}
          hint="Optional"
          onChange={(e) => onFieldChange(which, 'email', e.target.value)}
        />
      </div>
    </Card>
  );
}

const ShipmentCreatePage = () => {
  const { permissions, organization } = useAuth();
  const navigate = useNavigate();
  const formId = useId();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [status, setStatus] = useState('BOOKED');
  const [service_type, setServiceType] = useState('STANDARD');
  const [reference_number, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const [pickupDate, setPickupDate] = useState(() => todayDateInputValue());
  const [paymentMethod, setPaymentMethod] = useState(PAYMENT_COD);
  const [codAmount, setCodAmount] = useState('');
  const [currency, setCurrency] = useState('PKR');
  const [sender, setSender] = useState(() => emptyParty());
  const [receiver, setReceiver] = useState(() => emptyParty());
  const [parcel, setParcel] = useState({
    weight_kg: '1',
    quantity: '1',
    package_type: 'BOX',
    description: '',
    length_cm: '',
    width_cm: '',
    height_cm: '',
  });

  if (!permissions.canWriteShipments) {
    return (
      <EmptyState
        title="Not allowed"
        description="Your role cannot create ORVIA shipments."
        actionLabel="Back to shipments"
        to="/app/shipments"
      />
    );
  }

  const onPartyField = (which, field, value) => {
    if (which === 'sender') {
      setSender((prev) => ({ ...prev, [field]: value }));
      return;
    }
    setReceiver((prev) => ({ ...prev, [field]: value }));
  };

  const formState = {
    sender,
    receiver,
    parcel,
    status,
    service_type,
    reference_number,
    notes,
    pickupDate,
    paymentMethod,
    codAmount,
    currency,
  };

  const codSummary =
    paymentMethod === PAYMENT_COD ? codCollectSummary(codAmount, currency) : null;

  const submit = async (event) => {
    event.preventDefault();
    setFormError('');
    const local = validateShipmentCreateForm(formState);
    if (Object.keys(local).length) {
      setErrors(local);
      toast.error('Please check the highlighted fields.');
      return;
    }
    setLoading(true);
    setErrors({});
    try {
      const payload = buildCreateShipmentPayload(formState);

      if (import.meta.env.DEV) {
        console.info('[Softorica] POST /shipments', payload);
      }

      const res = await shipmentApi.create(payload);
      const created = res.data;
      if (!created?.id || !created?.tracking_number) {
        throw new Error('Shipment response missing id or tracking_number');
      }
      if (created.sender?.name !== payload.sender.name || created.receiver?.name !== payload.receiver.name) {
        console.warn('[Softorica] sender/receiver mismatch in API response', {
          sent: { sender: payload.sender.name, receiver: payload.receiver.name },
          got: { sender: created.sender?.name, receiver: created.receiver?.name },
        });
      }
      toast.success(`Shipment created · ${created.tracking_number}`);
      navigate(`/app/shipments/${created.id}/receipt`, {
        replace: true,
        state: { shipment: created },
      });
    } catch (error) {
      const fieldErrors = getValidationDetails(error);
      setErrors(fieldErrors);
      const message = getApiErrorMessage(error, 'Could not create shipment');
      setFormError(message);
      toast.error(message);
      if (import.meta.env.DEV) {
        console.error('[Softorica] create shipment failed', {
          status: error?.response?.status,
          url: `${error?.config?.baseURL || ''}${error?.config?.url || ''}`,
          data: error?.response?.data,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const minPickup = todayDateInputValue();

  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-fade-up">
      <SectionHeading
        title="Create shipment"
        description={
          organization
            ? `ORVIA workspace · ${organization.name}`
            : 'ORVIA tenant shipment booking'
        }
        action={
          <Button to="/app/shipments" variant="outline" size="sm">
            Cancel
          </Button>
        }
      />

      {formError && (
        <div className="rounded-md border border-danger/20 bg-danger-soft px-4 py-3 text-sm text-danger">
          {formError}
        </div>
      )}

      <form key={formId} onSubmit={submit} className="space-y-6" autoComplete="off" noValidate>
        <PartyFields
          which="sender"
          value={sender}
          title="1. Sender Information"
          errors={errors}
          onFieldChange={onPartyField}
          formId={formId}
        />
        <PartyFields
          which="receiver"
          value={receiver}
          title="2. Receiver Information"
          errors={errors}
          onFieldChange={onPartyField}
          formId={formId}
        />

        <Card className="space-y-4 p-5">
          <h2 className="font-display text-lg text-ink">3. Parcel Details</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Select
              label="Package type"
              name={`${formId}-package`}
              id={`${formId}-package`}
              required
              value={parcel.package_type}
              error={errors.package_type}
              onChange={(e) => setParcel((p) => ({ ...p, package_type: e.target.value }))}
            >
              <option value="BOX">Box</option>
              <option value="ENVELOPE">Envelope</option>
              <option value="BAG">Bag</option>
              <option value="OTHER">Other</option>
            </Select>
            <Input
              label="Weight (kg)"
              name={`${formId}-weight`}
              id={`${formId}-weight`}
              required
              autoComplete="off"
              inputMode="decimal"
              value={parcel.weight_kg}
              error={errors.weight_kg}
              onChange={(e) => setParcel((p) => ({ ...p, weight_kg: e.target.value }))}
            />
            <Input
              label="Pieces"
              name={`${formId}-pieces`}
              id={`${formId}-pieces`}
              required
              autoComplete="off"
              inputMode="numeric"
              value={parcel.quantity}
              error={errors.quantity}
              onChange={(e) => setParcel((p) => ({ ...p, quantity: e.target.value }))}
            />
            <Input
              label="Length (cm)"
              name={`${formId}-length`}
              id={`${formId}-length`}
              autoComplete="off"
              inputMode="decimal"
              value={parcel.length_cm}
              hint="Optional"
              onChange={(e) => setParcel((p) => ({ ...p, length_cm: e.target.value }))}
            />
            <Input
              label="Width (cm)"
              name={`${formId}-width`}
              id={`${formId}-width`}
              autoComplete="off"
              inputMode="decimal"
              value={parcel.width_cm}
              hint="Optional"
              onChange={(e) => setParcel((p) => ({ ...p, width_cm: e.target.value }))}
            />
            <Input
              label="Height (cm)"
              name={`${formId}-height`}
              id={`${formId}-height`}
              autoComplete="off"
              inputMode="decimal"
              value={parcel.height_cm}
              hint="Optional"
              onChange={(e) => setParcel((p) => ({ ...p, height_cm: e.target.value }))}
            />
            <Select
              label="Delivery / service type"
              name={`${formId}-service`}
              id={`${formId}-service`}
              required
              value={service_type}
              error={errors.service_type}
              onChange={(e) => setServiceType(e.target.value)}
            >
              <option value="STANDARD">Standard</option>
              <option value="EXPRESS">Express</option>
              <option value="SAME_DAY">Same day</option>
            </Select>
            <Select
              label="Initial status"
              name={`${formId}-status`}
              id={`${formId}-status`}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="BOOKED">Booked</option>
              <option value="DRAFT">Draft</option>
            </Select>
            <Input
              label="Order reference"
              name={`${formId}-reference`}
              id={`${formId}-reference`}
              autoComplete="off"
              value={reference_number}
              hint="Optional"
              onChange={(e) => setReference(e.target.value)}
            />
            <div className="sm:col-span-2 lg:col-span-3">
              <Input
                label="Parcel description"
                name={`${formId}-desc`}
                id={`${formId}-desc`}
                autoComplete="off"
                value={parcel.description}
                hint="Optional"
                onChange={(e) => setParcel((p) => ({ ...p, description: e.target.value }))}
              />
            </div>
          </div>
        </Card>

        <Card className="space-y-4 p-5">
          <h2 className="font-display text-lg text-ink">4. Pickup Schedule & Payment</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Pickup Date"
              type="date"
              name={`${formId}-pickup`}
              id={`${formId}-pickup`}
              required
              min={minPickup}
              value={pickupDate}
              error={errors.pickup_date}
              onChange={(e) => setPickupDate(e.target.value)}
            />
            <Select
              label="Payment Method"
              name={`${formId}-payment`}
              id={`${formId}-payment`}
              required
              value={paymentMethod}
              error={errors.payment_method}
              onChange={(e) => setPaymentMethod(e.target.value)}
            >
              <option value={PAYMENT_COD}>Cash on Delivery (COD)</option>
              <option value={PAYMENT_PREPAID}>Prepaid</option>
            </Select>
          </div>

          {paymentMethod === PAYMENT_COD && (
            <div className="space-y-4 rounded-md border border-olive/25 bg-olive/5 p-4">
              <div>
                <p className="text-sm font-semibold text-olive">Cash on Delivery (COD)</p>
                <p className="mt-1 text-xs text-ink-secondary">
                  COD amount is stored on the ORVIA shipment (`cod_amount` + `currency`).
                  ORVIA does not calculate separate COD service charges.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="COD Amount"
                  name={`${formId}-cod`}
                  id={`${formId}-cod`}
                  required
                  autoComplete="off"
                  inputMode="decimal"
                  placeholder="0.00"
                  value={codAmount}
                  error={errors.cod_amount}
                  onChange={(e) => setCodAmount(e.target.value)}
                />
                <Input
                  label="Currency"
                  name={`${formId}-currency`}
                  id={`${formId}-currency`}
                  required
                  autoComplete="off"
                  maxLength={3}
                  value={currency}
                  error={errors.currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                />
              </div>
              <dl className="grid gap-2 rounded-md border border-line bg-surface px-4 py-3 text-sm sm:grid-cols-3">
                <div>
                  <dt className="text-xs uppercase tracking-[0.12em] text-ink-muted">COD to Collect</dt>
                  <dd className="mt-1 font-semibold text-ink">
                    {codSummary?.codToCollect != null
                      ? `${codSummary.currency} ${codSummary.codToCollect}`
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.12em] text-ink-muted">
                    COD Service Charges
                  </dt>
                  <dd className="mt-1 font-semibold text-ink-secondary">Not applied</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.12em] text-ink-muted">
                    Total Collectable Amount
                  </dt>
                  <dd className="mt-1 font-semibold text-olive">
                    {codSummary?.totalCollectable != null
                      ? `${codSummary.currency} ${codSummary.totalCollectable}`
                      : '—'}
                  </dd>
                </div>
              </dl>
            </div>
          )}

          <Textarea
            label="Remarks"
            name={`${formId}-notes`}
            id={`${formId}-notes`}
            autoComplete="off"
            value={notes}
            hint="Optional"
            onChange={(e) => setNotes(e.target.value)}
          />
        </Card>

        <Card className="space-y-3 p-5">
          <h2 className="font-display text-lg text-ink">5. Shipment Summary</h2>
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-ink-muted">Sender</dt>
              <dd className="font-semibold text-ink">{sender.name || '—'} · {sender.city || '—'}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Receiver</dt>
              <dd className="font-semibold text-ink">
                {receiver.name || '—'} · {receiver.city || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-ink-muted">Pickup</dt>
              <dd className="font-semibold text-ink">{pickupDate || '—'}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Payment</dt>
              <dd className="font-semibold text-ink">
                {paymentMethod === PAYMENT_COD
                  ? `COD${codSummary?.codToCollect != null ? ` · ${codSummary.currency} ${codSummary.codToCollect}` : ''}`
                  : 'Prepaid'}
              </dd>
            </div>
          </dl>
          <div className="flex flex-wrap gap-3 pt-2">
            <Button type="submit" disabled={loading} className="min-w-[12rem]">
              {loading ? 'Creating shipment…' : 'Create Shipment'}
            </Button>
            <Button type="button" variant="outline" to="/app/shipments" disabled={loading}>
              Cancel
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
};

export default ShipmentCreatePage;
