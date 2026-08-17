/**
 * Unit checks for Softorica shipment form helpers (no React / no network).
 * Run: node scripts/shipment-form-unit.mjs
 */
import assert from 'node:assert/strict';
import {
  PAYMENT_COD,
  PAYMENT_PREPAID,
  buildCreateShipmentPayload,
  codCollectSummary,
  emptyParty,
  normalizeMoney2,
  pickupDateToApi,
  todayDateInputValue,
  updatePartyField,
  validateShipmentCreateForm,
} from '../src/utils/shipmentForm.js';

const ORVIA_RE = /^ORVIA-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{10}$/;
const GBQ_RE = /^GBQ\d{7,}$/i;

function isOrvia(v) {
  return ORVIA_RE.test(String(v || '').trim().toUpperCase());
}
function isGbq(v) {
  const cleaned = String(v || '').trim().toUpperCase();
  return GBQ_RE.test(cleaned) && cleaned.length >= 10;
}

// Sender / receiver independence
let sender = emptyParty();
let receiver = emptyParty();
sender = updatePartyField(sender, 'name', 'Alice Sender');
sender = updatePartyField(sender, 'phone', '03001111111');
sender = updatePartyField(sender, 'city', 'Lahore');
sender = updatePartyField(sender, 'address', 'Sender St');
receiver = updatePartyField(receiver, 'name', 'Bob Receiver');
receiver = updatePartyField(receiver, 'phone', '03002222222');
receiver = updatePartyField(receiver, 'city', 'Karachi');
receiver = updatePartyField(receiver, 'address', 'Receiver Ave');
assert.equal(sender.name, 'Alice Sender');
assert.equal(receiver.name, 'Bob Receiver');
assert.notEqual(sender.name, receiver.name);
assert.notEqual(sender.phone, receiver.phone);
assert.notEqual(sender.city, receiver.city);

sender = updatePartyField(sender, 'name', 'Changed Sender Only');
assert.equal(sender.name, 'Changed Sender Only');
assert.equal(receiver.name, 'Bob Receiver');

const today = todayDateInputValue();
const baseState = {
  sender,
  receiver,
  parcel: { weight_kg: '1.5', quantity: '1', package_type: 'BOX', description: '' },
  service_type: 'STANDARD',
  status: 'BOOKED',
  reference_number: 'REF-1',
  notes: '',
  pickupDate: today,
  paymentMethod: PAYMENT_COD,
  codAmount: '1500.5',
  currency: 'PKR',
};

// COD validation
const missingCod = validateShipmentCreateForm({ ...baseState, codAmount: '' });
assert.ok(missingCod.cod_amount, 'COD amount required when COD');

const badCod = validateShipmentCreateForm({ ...baseState, codAmount: '12.345' });
assert.ok(badCod.cod_amount, 'COD rejects >2 decimals');

const okCod = validateShipmentCreateForm(baseState);
assert.deepEqual(okCod, {});

// Prepaid hides COD requirement
const prepaidErrors = validateShipmentCreateForm({
  ...baseState,
  paymentMethod: PAYMENT_PREPAID,
  codAmount: '',
});
assert.equal(prepaidErrors.cod_amount, undefined);

const prepaidPayload = buildCreateShipmentPayload({
  ...baseState,
  paymentMethod: PAYMENT_PREPAID,
  codAmount: '999',
});
assert.equal(prepaidPayload.cod_amount, null);
assert.equal(prepaidPayload.currency, null);
assert.equal(prepaidPayload.sender.name, 'Changed Sender Only');
assert.equal(prepaidPayload.receiver.name, 'Bob Receiver');
assert.notEqual(prepaidPayload.sender.name, prepaidPayload.receiver.name);

const codPayload = buildCreateShipmentPayload(baseState);
assert.equal(codPayload.cod_amount, '1500.50');
assert.equal(codPayload.currency, 'PKR');
assert.equal(codPayload.pickup_at, pickupDateToApi(today));
assert.equal(codPayload.sender.city, 'Lahore');
assert.equal(codPayload.receiver.city, 'Karachi');

const summary = codCollectSummary('1500.5', 'PKR');
assert.equal(summary.codToCollect, '1500.50');
assert.equal(summary.codServiceCharges, null);
assert.equal(summary.totalCollectable, '1500.50');

assert.equal(normalizeMoney2('100'), '100.00');
assert.equal(normalizeMoney2('100.1'), '100.10');
assert.equal(normalizeMoney2('abc'), null);

assert.equal(isOrvia('ORVIA-ABCDEFGHJK'), true);
assert.equal(isOrvia('GBQ12345678'), false);
assert.equal(isGbq('GBQ12345678'), true);
assert.equal(isGbq('ORVIA-ABCDEFGHJK'), false);

console.log('PASS shipment-form-unit');
