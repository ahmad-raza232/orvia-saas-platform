/**
 * Softorica SaaS shipment create helpers.
 * Maps UI state to CreateShipmentRequest fields only (no invented API keys).
 *
 * Backend accepts: sender, receiver, parcel, service_type, reference_number,
 * notes, pickup_at, cod_amount, currency, status, customer_id.
 * There is no payment_method or COD service-charge field on the SaaS API.
 */

export const PAYMENT_COD = 'COD';
export const PAYMENT_PREPAID = 'PREPAID';

export function emptyParty() {
  return {
    name: '',
    phone: '',
    email: '',
    address: '',
    city: '',
    state: '',
    country: 'PK',
    postal_code: '',
  };
}

export function todayDateInputValue(now = new Date()) {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** Normalize money to a 2-decimal string without floating-point math. */
export function normalizeMoney2(value) {
  const cleaned = String(value ?? '')
    .trim()
    .replace(/,/g, '');
  if (cleaned === '') return null;
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  const [whole, frac = ''] = cleaned.split('.');
  return `${whole}.${(frac + '00').slice(0, 2)}`;
}

export function isValidPhone(value) {
  const cleaned = String(value || '').trim();
  if (cleaned.length < 7 || cleaned.length > 32) return false;
  return /^[+]?[\d\s()-]{7,32}$/.test(cleaned) && /\d{7,}/.test(cleaned.replace(/\D/g, ''));
}

export function isValidMoney2(value) {
  return normalizeMoney2(value) !== null;
}

export function pickupDateToApi(pickupDate) {
  const date = String(pickupDate || '').trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  // Naive local morning slot; backend stores timestamptz-compatible datetime.
  return `${date}T09:00:00`;
}

export function formatPickupDisplay(pickupAt) {
  if (!pickupAt) return '—';
  const raw = String(pickupAt);
  const datePart = raw.slice(0, 10);
  if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
    const [y, m, d] = datePart.split('-');
    return `${d}/${m}/${y}`;
  }
  try {
    return new Date(pickupAt).toLocaleDateString('en-GB');
  } catch {
    return raw;
  }
}

export function paymentMethodFromShipment(shipment) {
  if (shipment?.cod_amount != null && shipment.cod_amount !== '') {
    return PAYMENT_COD;
  }
  return PAYMENT_PREPAID;
}

/**
 * Mutate a party clone — used by unit tests to prove sender/receiver independence.
 */
export function updatePartyField(party, field, value) {
  return { ...party, [field]: value };
}

export function validateShipmentCreateForm(state) {
  const {
    sender,
    receiver,
    parcel,
    pickupDate,
    paymentMethod,
    codAmount,
    currency,
  } = state;
  const next = {};

  if (!sender?.name?.trim()) next.sender_name = 'Shipper name is required';
  if (!sender?.phone?.trim()) next.sender_phone = 'Shipper contact is required';
  else if (!isValidPhone(sender.phone)) next.sender_phone = 'Enter a valid phone number';
  if (!sender?.address?.trim()) next.sender_address = 'Pickup address is required';
  if (!sender?.city?.trim()) next.sender_city = 'Origin city is required';

  if (!receiver?.name?.trim()) next.receiver_name = 'Consignee name is required';
  if (!receiver?.phone?.trim()) next.receiver_phone = 'Consignee contact is required';
  else if (!isValidPhone(receiver.phone)) next.receiver_phone = 'Enter a valid phone number';
  if (!receiver?.address?.trim()) next.receiver_address = 'Delivery address is required';
  if (!receiver?.city?.trim()) next.receiver_city = 'Destination city is required';

  if (!parcel?.package_type?.trim()) next.package_type = 'Package type is required';
  if (!parcel?.weight_kg || Number(parcel.weight_kg) <= 0) {
    next.weight_kg = 'Weight must be greater than 0';
  }
  if (!parcel?.quantity || Number(parcel.quantity) < 1) {
    next.quantity = 'Pieces must be at least 1';
  }
  if (!state.service_type) next.service_type = 'Delivery / service type is required';

  if (!pickupDate) {
    next.pickup_date = 'Pickup date is required';
  } else if (!/^\d{4}-\d{2}-\d{2}$/.test(pickupDate)) {
    next.pickup_date = 'Pickup date is invalid';
  } else {
    const today = todayDateInputValue();
    if (pickupDate < today) {
      next.pickup_date = 'Pickup date cannot be in the past';
    }
  }

  if (paymentMethod !== PAYMENT_COD && paymentMethod !== PAYMENT_PREPAID) {
    next.payment_method = 'Payment method is required';
  }

  if (paymentMethod === PAYMENT_COD) {
    const money = normalizeMoney2(codAmount);
    if (money === null) {
      next.cod_amount = 'Valid COD amount is required (0.00 or greater, max 2 decimals)';
    }
    if (!String(currency || '').trim()) {
      next.currency = 'Currency is required for COD';
    }
  }

  return next;
}

/**
 * Build CreateShipmentRequest body. Sender/receiver come from separate objects only.
 */
export function buildCreateShipmentPayload(state) {
  const {
    sender,
    receiver,
    parcel,
    status = 'BOOKED',
    service_type = 'STANDARD',
    reference_number = '',
    notes = '',
    pickupDate,
    paymentMethod,
    codAmount,
    currency = 'PKR',
  } = state;

  const payload = {
    status,
    service_type,
    reference_number: String(reference_number || '').trim() || null,
    notes: String(notes || '').trim() || null,
    pickup_at: pickupDateToApi(pickupDate),
    sender: {
      name: sender.name.trim(),
      phone: sender.phone.trim(),
      email: sender.email.trim() || null,
      address: sender.address.trim(),
      city: sender.city.trim(),
      state: sender.state.trim() || null,
      postal_code: sender.postal_code.trim() || null,
      country: (sender.country || 'PK').trim().toUpperCase(),
    },
    receiver: {
      name: receiver.name.trim(),
      phone: receiver.phone.trim(),
      email: receiver.email.trim() || null,
      address: receiver.address.trim(),
      city: receiver.city.trim(),
      state: receiver.state.trim() || null,
      postal_code: receiver.postal_code.trim() || null,
      country: (receiver.country || 'PK').trim().toUpperCase(),
    },
    parcel: {
      weight_kg: String(parcel.weight_kg).trim(),
      quantity: Number(parcel.quantity) || 1,
      package_type: parcel.package_type.trim() || null,
      description: String(parcel.description || '').trim() || null,
      length_cm: String(parcel.length_cm || '').trim() || null,
      width_cm: String(parcel.width_cm || '').trim() || null,
      height_cm: String(parcel.height_cm || '').trim() || null,
    },
  };

  if (paymentMethod === PAYMENT_COD) {
    payload.cod_amount = normalizeMoney2(codAmount);
    payload.currency = String(currency || 'PKR').trim().toUpperCase() || 'PKR';
  } else {
    payload.cod_amount = null;
    payload.currency = null;
  }

  return payload;
}

/** Softorica SaaS does not compute COD service charges — display honesty helpers. */
export function codCollectSummary(codAmount, currency = 'PKR') {
  const amount = normalizeMoney2(codAmount);
  return {
    codToCollect: amount,
    currency: String(currency || 'PKR').toUpperCase(),
    /** Not provided by Softorica Modules 1–11 API — do not invent. */
    codServiceCharges: null,
    totalCollectable: amount,
  };
}
