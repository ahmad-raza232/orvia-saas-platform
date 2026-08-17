export const formatStatus = (status) =>
  String(status ?? '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

export const formatDate = (dateString, withTime = false) => {
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
    });
  } catch {
    return dateString;
  }
};

export const formatMoney = (value) => {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return '0.00';
  return numericValue.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

export const statusTone = (status) => {
  const value = String(status ?? '').toLowerCase();
  if (value === 'delivered' || value === 'active' || value === 'uploaded' || value === 'sent') {
    return 'success';
  }
  if (['in_transit', 'picked_up', 'out_for_delivery', 'booked'].includes(value)) return 'info';
  if (['pending', 'confirmed', 'draft', 'sending'].includes(value)) return 'warning';
  if (['cancelled', 'failed', 'expired', 'inactive', 'suspended'].includes(value)) {
    return 'danger';
  }
  return 'neutral';
};
