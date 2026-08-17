import React, { useRef, useState, useEffect } from 'react';
import html2canvas from 'html2canvas';

const BookingReceipt = ({ booking, onClose }) => {
  const receiptRef = useRef();
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    // Generate QR code URL using api.qrserver.com (no dependencies needed)
    if (booking?.trackingId) {
      const url = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(booking.trackingId)}&format=png&ecc=L`;
      setQrCodeUrl(url);
    }
  }, [booking?.trackingId]);

  const priceLabel = Number(booking?.price || 0).toLocaleString();
  const paymentLabel = String(booking?.paymentMethod || 'n/a').toUpperCase();
  const packageType = String(booking?.packageType || 'standard');
  const packageLabel = packageType.charAt(0).toUpperCase() + packageType.slice(1);

  const handlePrint = () => {
    if (!qrCodeUrl) {
      alert('Please wait for QR code to generate...');
      return;
    }
    
    const printWindow = window.open('', '', 'width=800,height=600');
    if (!printWindow) {
      alert('Please allow popups to print the receipt.');
      return;
    }
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Receipt - ${booking.trackingId}</title>
          <style>
            * { 
              margin: 0; 
              padding: 0; 
              box-sizing: border-box; 
            }
            
            body { 
              font-family: Arial, sans-serif;
              background: white;
              padding: 5mm;
              font-size: 9px;
            }
            
            .receipt-container {
              max-width: 100%;
              margin: 0 auto;
              background: white;
            }
            
            .header {
              display: flex;
              justify-content: space-between;
              align-items: center;
              border-bottom: 3px solid #000;
              padding-bottom: 4px;
              margin-bottom: 5px;
            }
            
            .logo {
              font-size: 22px;
              font-weight: bold;
              color: #000;
            }
            
            .header-right {
              display: flex;
              gap: 8px;
              align-items: center;
            }
            
            .barcode-section {
              text-align: center;
            }
            
            .barcode-box {
              width: 55px;
              height: 20px;
              background: repeating-linear-gradient(90deg, #000 0px, #000 1px, #fff 1px, #fff 2px);
              margin-bottom: 2px;
            }
            
            .barcode-number {
              font-size: 7px;
              font-weight: bold;
              color: #000;
            }
            
            .lhe-tag {
              font-size: 12px;
              font-weight: bold;
              padding: 3px 7px;
              border: 2px solid #000;
              color: #000;
            }
            
            .main-grid {
              display: grid;
              grid-template-columns: 1fr 1fr 1fr;
              gap: 5px;
              margin-bottom: 5px;
            }
            
            .section {
              border: 1px solid #000;
              background: #fff;
              display: flex;
              flex-direction: column;
              min-height: 80px;
            }
            
            .section-title {
              background: #e5e7eb;
              padding: 2px 4px;
              font-weight: bold;
              font-size: 9px;
              color: #000;
              border-bottom: 1px solid #000;
            }
            
            .section-content {
              padding: 4px;
              flex: 1;
              display: flex;
              flex-direction: column;
            }
            
            .field {
              display: flex;
              margin-bottom: 2px;
              font-size: 8px;
              line-height: 1.2;
            }
            
            .field-label {
              font-weight: bold;
              min-width: 50px;
              color: #000;
              flex-shrink: 0;
            }
            
            .field-value {
              flex: 1;
              color: #000;
              word-break: break-word;
            }
            
            .small-text {
              font-size: 7px;
            }
            
            .qr-section {
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: flex-start;
            }
            
            .qr-code {
              width: 70px;
              height: 70px;
              border: 2px solid #000;
              display: flex;
              align-items: center;
              justify-content: center;
              background: white;
              margin-bottom: 3px;
              overflow: hidden;
            }
            
            .qr-code img {
              width: 100%;
              height: 100%;
              object-fit: contain;
              display: block;
            }
            
            .order-info {
              width: 100%;
            }
            
            .order-info-row {
              display: flex;
              justify-content: space-between;
              font-size: 8px;
              margin-bottom: 1px;
            }
            
            .order-info-label {
              font-weight: bold;
              color: #000;
            }
            
            .order-info-value {
              font-weight: bold;
              color: #000;
            }
            
            .shipper-section {
              grid-column: 1 / 3;
              min-height: 60px;
            }
            
            .shipper-grid {
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 2px 8px;
            }
            
            .shipper-field-full {
              grid-column: 1 / -1;
            }
            
            .payment-section {
              display: flex;
              align-items: center;
              justify-content: center;
              flex: 1;
            }
            
            .payment-text {
              font-size: 16px;
              font-weight: bold;
              color: #000;
            }
            
            .order-details {
              border: 1px solid #000;
              background: #fff;
              padding: 3px 4px;
              margin-bottom: 4px;
            }
            
            .order-details-text {
              font-size: 8px;
              color: #000;
            }
            
            .footer {
              border-top: 3px solid #000;
              padding-top: 3px;
              text-align: center;
              font-size: 7px;
              color: #555;
            }
            
            .footer p {
              margin-bottom: 1px;
              line-height: 1.3;
            }
            
            @media print {
              body { 
                padding: 3mm;
                margin: 0;
              }
              
              @page { 
                size: A5 landscape;
                margin: 3mm;
              }
            }
          </style>
        </head>
        <body>
          <div class="receipt-container">
            <div class="header">
              <div class="logo">GoBurq</div>
              <div class="header-right">
                <div class="barcode-section">
                  <div class="barcode-box"></div>
                  <div class="barcode-number">#GBQ${booking.trackingId?.slice(-3) || '891'}</div>
                </div>
                <div class="barcode-section">
                  <div class="barcode-box"></div>
                  <div class="barcode-number">${booking.trackingId || 'GBQ8910330380CH9'}</div>
                </div>
                <div class="lhe-tag">LHE</div>
              </div>
            </div>

            <div class="main-grid">
              <div class="section">
                <div class="section-title">Consignee Information</div>
                <div class="section-content">
                  <div class="field">
                    <span class="field-label">Name:</span>
                    <span class="field-value">${booking.receiverName}</span>
                  </div>
                  <div class="field">
                    <span class="field-label">Contact:</span>
                    <span class="field-value">${booking.receiverPhone}</span>
                  </div>
                  <div class="field">
                    <span class="field-label">Delivery Address:</span>
                    <span class="field-value small-text">${booking.receiverAddress}</span>
                  </div>
                </div>
              </div>

              <div class="section">
                <div class="section-title">Shipment Information</div>
                <div class="section-content">
                  <div class="field">
                    <span class="field-label">Pieces:</span>
                    <span class="field-value">1</span>
                  </div>
                  <div class="field">
                    <span class="field-label">Order Ref:</span>
                    <span class="field-value">#${booking.orderId || '174274'}</span>
                  </div>
                  <div class="field">
                    <span class="field-label">Tracking No:</span>
                    <span class="field-value small-text">${booking.trackingId}</span>
                  </div>
                  <div class="field">
                    <span class="field-label">Origin:</span>
                    <span class="field-value">${booking.senderCity}</span>
                  </div>
                  <div class="field">
                    <span class="field-label">Destination:</span>
                    <span class="field-value">${booking.receiverCity}</span>
                  </div>
                </div>
              </div>

              <div class="section">
                <div class="section-title">Order Information</div>
                <div class="section-content qr-section">
                  <div class="qr-code">
                    <img src="${qrCodeUrl}" alt="QR Code" crossorigin="anonymous" />
                  </div>
                  <div class="order-info">
                    <div class="order-info-row">
                      <span class="order-info-label">Amount:</span>
                      <span class="order-info-value">${priceLabel}.00/-</span>
                    </div>
                    ${booking.paymentMethod === 'cod' && booking.codAmount ? `
                    <div class="order-info-row">
                      <span class="order-info-label">COD Collect:</span>
                      <span class="order-info-value">${Number(booking.codAmount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/-</span>
                    </div>
                    <div class="order-info-row">
                      <span class="order-info-label">COD Charges:</span>
                      <span class="order-info-value">${Number(booking.codServiceCharges || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/-</span>
                    </div>
                    ` : ''}
                    <div class="order-info-row">
                      <span class="order-info-label">Date:</span>
                      <span class="order-info-value">${new Date(booking.pickupDate).toLocaleDateString('en-GB')}</span>
                    </div>
                    <div class="order-info-row">
                      <span class="order-info-label">Order Type:</span>
                      <span class="order-info-value">${booking.deliveryType === 'express' ? 'Express' : 'Overland'}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="main-grid">
              <div class="section shipper-section">
                <div class="section-title">Shipper Information</div>
                <div class="section-content">
                  <div class="shipper-grid">
                    <div class="field">
                      <span class="field-label">Name:</span>
                      <span class="field-value">${booking.senderName}</span>
                    </div>
                    <div class="field">
                      <span class="field-label">Return City:</span>
                      <span class="field-value">${booking.senderCity}</span>
                    </div>
                    <div class="field">
                      <span class="field-label">Contact:</span>
                      <span class="field-value">${booking.senderPhone}</span>
                    </div>
                    <div class="field">
                      <span class="field-label">Remarks:</span>
                      <span class="field-value small-text">${booking.description || 'Allow Open Parcel'}</span>
                    </div>
                    <div class="field shipper-field-full">
                      <span class="field-label">Pickup Address:</span>
                      <span class="field-value small-text">${booking.senderAddress}</span>
                    </div>
                    <div class="field shipper-field-full">
                      <span class="field-label">Return Address:</span>
                      <span class="field-value small-text">${booking.senderAddress}, ${booking.senderCity}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="section">
                <div class="section-title">Payment Method</div>
                <div class="section-content payment-section">
                  <span class="payment-text">${paymentLabel}</span>
                </div>
              </div>
            </div>

            <div class="order-details">
              <span class="order-details-text">
                <strong>Order Details:</strong> [ 1 x ${packageLabel} Package - ${booking.weight}kg ${booking.dimensions ? `- ${booking.dimensions}` : ''} ]
              </span>
            </div>

            <div class="footer">
              <p>
                <strong>Order Information:</strong> Track this shipment with your GoBurq tracking ID on the GoBurq tracking page
              </p>
              <p>Helpline: 0326 3253256 | GoBurq Support</p>
            </div>
          </div>
          
          <script>
            window.onload = function() {
              setTimeout(function() {
                window.print();
              }, 500);
            };
          </script>
        </body>
      </html>
    `);
    
    printWindow.document.close();
  };

  const handleDownload = async () => {
    if (!qrCodeUrl) {
      alert('Please wait for QR code to generate...');
      return;
    }

    if (!receiptRef.current || isDownloading) {
      return;
    }

    setIsDownloading(true);

    try {
      const canvas = await html2canvas(receiptRef.current, {
        backgroundColor: '#ffffff',
        scale: 2,
        useCORS: true,
        scrollY: -window.scrollY,
      });

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png', 1));
      if (!blob) {
        throw new Error('Unable to generate image');
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `receipt-${booking.trackingId || 'booking'}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);
      alert('Download failed. Please try again or use Print to save as PDF.');
    } finally {
      setIsDownloading(false);
    }
  };

  if (!booking) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-auto bg-ink/40 p-4 backdrop-blur-[2px]">
      <div className="w-full max-w-5xl rounded-lg border border-line bg-surface shadow-md">
        <div className="p-4">
          <div ref={receiptRef} className="bg-white">
            <div className="flex justify-between items-center border-b-2 border-black pb-2 mb-3">
              <div className="text-3xl font-bold tracking-[0.14em] text-gray-900">GoBurq</div>
              <div className="flex gap-4 items-center">
                <div className="text-center">
                  <div className="h-8 w-20 bg-black flex items-center justify-center overflow-hidden">
                    <div className="w-full h-full" style={{
                      background: 'repeating-linear-gradient(90deg, #fff 0px, #fff 2px, #000 2px, #000 4px)'
                    }}></div>
                  </div>
                  <div className="text-xs font-bold mt-1 text-gray-900">#{booking.trackingId?.slice(0, 6) || '19713'}</div>
                </div>
                <div className="text-center">
                  <div className="h-8 w-20 bg-black flex items-center justify-center overflow-hidden">
                    <div className="w-full h-full" style={{
                      background: 'repeating-linear-gradient(90deg, #fff 0px, #fff 2px, #000 2px, #000 4px)'
                    }}></div>
                  </div>
                  <div className="text-xs font-bold mt-1 text-gray-900">{booking.trackingId || '252472800065563'}</div>
                </div>
                <div className="text-xl font-bold border-2 border-black px-3 py-1 text-gray-900">
                  LHE
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-3">
              <div className="border border-gray-300 bg-gray-50">
                <div className="bg-gray-200 px-2 py-1 border-b border-gray-300 font-bold text-xs text-gray-900">
                  Consignee Information
                </div>
                <div className="p-2 space-y-1 text-[10px]">
                  <div className="flex">
                    <span className="font-bold min-w-[60px] text-gray-900">Name:</span>
                    <span className="flex-1 text-gray-900">{booking.receiverName}</span>
                  </div>
                  <div className="flex">
                    <span className="font-bold min-w-[60px] text-gray-900">Contact:</span>
                    <span className="flex-1 text-gray-900">{booking.receiverPhone}</span>
                  </div>
                  <div className="flex">
                    <span className="font-bold min-w-[60px] text-gray-900">Delivery Address:</span>
                    <span className="flex-1 text-[9px] text-gray-900">{booking.receiverAddress}</span>
                  </div>
                </div>
              </div>

              <div className="border border-gray-300 bg-gray-50">
                <div className="bg-gray-200 px-2 py-1 border-b border-gray-300 font-bold text-xs text-gray-900">
                  Shipment Information
                </div>
                <div className="p-2 space-y-1 text-[10px]">
                  <div className="flex">
                    <span className="font-bold min-w-[70px] text-gray-900">Pieces:</span>
                    <span className="text-gray-900">1</span>
                  </div>
                  <div className="flex">
                    <span className="font-bold min-w-[70px] text-gray-900">Order Ref:</span>
                    <span className="text-gray-900">#{booking.orderId || Math.floor(Math.random() * 100000)}</span>
                  </div>
                  <div className="flex">
                    <span className="font-bold min-w-[70px] text-gray-900">Tracking No:</span>
                    <span className="text-[9px] text-gray-900">{booking.trackingId}</span>
                  </div>
                  <div className="flex">
                    <span className="font-bold min-w-[70px] text-gray-900">Origin:</span>
                    <span className="text-gray-900">{booking.senderCity}</span>
                  </div>
                  <div className="flex">
                    <span className="font-bold min-w-[70px] text-gray-900">Destination:</span>
                    <span className="text-gray-900">{booking.receiverCity}</span>
                  </div>
                </div>
              </div>

              <div className="border border-gray-300 bg-gray-50">
                <div className="bg-gray-200 px-2 py-1 border-b border-gray-300 font-bold text-xs text-gray-900">
                  Order Information
                </div>
                <div className="p-2 flex flex-col items-center justify-between h-[calc(100%-28px)]">
                  <div className="w-24 h-24 border-2 border-black flex items-center justify-center bg-white p-1">
                    {qrCodeUrl ? (
                      <img 
                        src={qrCodeUrl} 
                        alt="QR Code" 
                        crossOrigin="anonymous"
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-xs text-gray-500">Loading QR...</div>
                    )}
                  </div>
                  <div className="text-center w-full mt-2">
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="font-bold text-gray-900">Amount:</span>
                      <span className="font-bold text-gray-900">{priceLabel}.00/-</span>
                    </div>
                    {booking.paymentMethod === 'cod' && booking.codAmount && (
                      <>
                        <div className="flex justify-between text-[10px] mb-1">
                          <span className="font-bold text-gray-900">COD Collect:</span>
                          <span className="font-bold text-gray-900">{Number(booking.codAmount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/-</span>
                        </div>
                        <div className="flex justify-between text-[10px] mb-1">
                          <span className="font-bold text-gray-900">COD Charges:</span>
                          <span className="font-bold text-gray-900">{Number(booking.codServiceCharges || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/-</span>
                        </div>
                      </>
                    )}
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="font-bold text-gray-900">Date:</span>
                      <span className="text-gray-900">{new Date(booking.pickupDate).toLocaleDateString('en-GB')}</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="font-bold text-gray-900">Order Type:</span>
                      <span className="text-gray-900">{booking.deliveryType === 'express' ? 'Express' : 'Overland'}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-3">
              <div className="border border-gray-300 bg-gray-50 col-span-2">
                <div className="bg-gray-200 px-2 py-1 border-b border-gray-300 font-bold text-xs text-gray-900">
                  Shipper Information
                </div>
                <div className="p-2">
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px]">
                    <div className="flex">
                      <span className="font-bold min-w-[80px] text-gray-900">Name:</span>
                      <span className="text-gray-900">{booking.senderName}</span>
                    </div>
                    <div className="flex">
                      <span className="font-bold min-w-[80px] text-gray-900">Return City:</span>
                      <span className="text-gray-900">{booking.senderCity}</span>
                    </div>
                    <div className="flex">
                      <span className="font-bold min-w-[80px] text-gray-900">Contact:</span>
                      <span className="text-gray-900">{booking.senderPhone}</span>
                    </div>
                    <div className="flex">
                      <span className="font-bold min-w-[80px] text-gray-900">Remarks:</span>
                      <span className="text-[9px] text-gray-900">{booking.description || 'Allow Open Parcel'}</span>
                    </div>
                    <div className="flex col-span-2">
                      <span className="font-bold min-w-[80px] text-gray-900">Pickup Address:</span>
                      <span className="text-[9px] text-gray-900">{booking.senderAddress}</span>
                    </div>
                    <div className="flex col-span-2">
                      <span className="font-bold min-w-[80px] text-gray-900">Return Address:</span>
                      <span className="text-[9px] text-gray-900">{booking.senderAddress}, {booking.senderCity}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="border border-gray-300 bg-gray-50">
                <div className="bg-gray-200 px-2 py-1 border-b border-gray-300 font-bold text-xs text-gray-900">
                  Payment Method
                </div>
                <div className="p-2 flex items-center justify-center h-[calc(100%-28px)]">
                  <span className="text-xl font-bold text-gray-900">
                    {paymentLabel}
                  </span>
                </div>
              </div>
            </div>

            <div className="border border-gray-300 bg-gray-50 mb-2">
              <div className="px-2 py-1">
                <span className="font-bold text-[10px] text-gray-900">Order Details: </span>
                <span className="text-[10px] text-gray-900">
                  [ 1 x {packageLabel} Package - 
                  {booking.weight}kg {booking.dimensions ? `- ${booking.dimensions}` : ''} ]
                </span>
              </div>
            </div>

            <div className="border-t-2 border-black pt-1 text-center text-[9px] text-gray-600">
              <p className="mb-1">
                <span className="font-bold">Order Information:</span> Track this shipment with your GoBurq tracking ID on the GoBurq tracking page
              </p>
              <p>Helpline: 0326 3253256 | GoBurq Support</p>
            </div>
          </div>

          <div className="mt-4 flex flex-col gap-3 border-t border-line pt-4 sm:flex-row">
            <button
              type="button"
              onClick={handlePrint}
              disabled={!qrCodeUrl}
              className={`flex-1 rounded-md py-3 font-semibold transition-colors ${qrCodeUrl ? 'bg-olive text-peach hover:bg-olive-hover' : 'cursor-not-allowed bg-muted text-ink-muted'}`}
            >
              {qrCodeUrl ? 'Print receipt' : 'Generating QR code...'}
            </button>
            <button
              type="button"
              onClick={handleDownload}
              disabled={!qrCodeUrl || isDownloading}
              className={`flex-1 rounded-md py-3 font-semibold transition-colors ${qrCodeUrl && !isDownloading ? 'bg-peach text-olive-dark hover:bg-peach-deep' : 'cursor-not-allowed bg-muted text-ink-muted'}`}
            >
              {isDownloading ? 'Downloading...' : 'Download receipt'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-md border border-line bg-surface py-3 font-semibold text-ink hover:bg-muted"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BookingReceipt;
