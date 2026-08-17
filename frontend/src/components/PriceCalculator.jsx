import { useState } from "react";
import { Calculator } from "lucide-react";
import Card from "./ui/Card";
import Button from "./ui/Button";
import Select from "./ui/Select";
import Input from "./ui/Input";

const PriceCalculator = () => {
  const [formData, setFormData] = useState({
    from: "",
    to: "",
    weight: "",
    packageType: "standard",
  });

  const [price, setPrice] = useState(null);
  const [breakdown, setBreakdown] = useState(null);

  const cities = [
    "Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad",
    "Multan", "Peshawar", "Quetta", "Sialkot", "Gujranwala",
    "Hyderabad", "Bahawalpur", "Sargodha", "Sukkur", "Larkana"
  ];

  const packageTypes = [
    { value: "document", label: "Document", multiplier: 1.0 },
    { value: "small", label: "Small Package", multiplier: 1.2 },
    { value: "medium", label: "Medium Package", multiplier: 1.5 },
    { value: "large", label: "Large Package", multiplier: 2.0 },
    { value: "fragile", label: "Fragile Item", multiplier: 2.5 },
  ];

  // Dummy Distance Matrix
  const calculateDistance = (from, to) => {
    const distances = {
      "Lahore-Karachi": 1200,
      "Lahore-Islamabad": 375,
      "Karachi-Islamabad": 1400,
      "Lahore-Faisalabad": 130,
      "Lahore-Multan": 340,
      "Karachi-Quetta": 690,
      "Islamabad-Peshawar": 180,
      "Multan-Faisalabad": 250,
    };

    const key = `${from}-${to}`;
    const reverseKey = `${to}-${from}`;

    return distances[key] || distances[reverseKey] || 500; // Default 500 km
  };

  const calculatePrice = () => {
    if (!formData.from || !formData.to || !formData.weight) {
      alert("Please fill all fields");
      return;
    }

    const baseRate = 100;
    const perKgRate = 50;
    const perKmRate = 2;

    const distance = calculateDistance(formData.from, formData.to);
    const pkg = packageTypes.find((p) => p.value === formData.packageType);

    const basePrice = baseRate;
    const weightCost = parseFloat(formData.weight) * perKgRate;
    const distanceCost = distance * perKmRate;

    const subtotal = basePrice + weightCost + distanceCost;
    const totalPrice = Math.round(subtotal * pkg.multiplier);

    setBreakdown({
      basePrice,
      weightCost,
      distanceCost,
      distance,
      multiplier: pkg.multiplier,
      packageType: pkg.label,
    });

    setPrice(totalPrice);
  };

  return (
    <section className="min-h-screen bg-canvas py-20">
      <div className="mx-auto max-w-4xl px-6">
        <h2 className="flex items-center gap-3 font-display text-h2 text-ink">
          <Calculator className="h-6 w-6 text-olive" /> Calculate delivery price
        </h2>
        <p className="mt-2 text-ink-secondary">
          Get an instant estimate for your parcel delivery across Pakistan.
        </p>

        <Card className="mt-10 p-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Select
              label="From city"
              value={formData.from}
              onChange={(e) => setFormData({ ...formData, from: e.target.value })}
            >
              <option value="">Select city</option>
              {cities.map((city) => (
                <option key={city} value={city}>{city}</option>
              ))}
            </Select>
            <Select
              label="To city"
              value={formData.to}
              onChange={(e) => setFormData({ ...formData, to: e.target.value })}
            >
              <option value="">Select city</option>
              {cities.map((city) => (
                <option key={city} value={city}>{city}</option>
              ))}
            </Select>
            <Input
              label="Weight (kg)"
              type="number"
              step="0.1"
              value={formData.weight}
              onChange={(e) => setFormData({ ...formData, weight: e.target.value })}
              placeholder="e.g., 2.5"
            />
            <Select
              label="Package type"
              value={formData.packageType}
              onChange={(e) => setFormData({ ...formData, packageType: e.target.value })}
            >
              {packageTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </Select>
          </div>
          <Button className="mt-6 w-full" onClick={calculatePrice}>
            Calculate price
          </Button>
        </Card>

        {price && breakdown && (
          <Card className="mt-8 p-6">
            <h3 className="font-display text-2xl text-ink">Estimated price</h3>
            <p className="mt-3 font-display text-4xl text-olive">PKR {price.toLocaleString()}</p>
            <div className="mt-4 space-y-2 text-sm text-ink-secondary">
              <p>Base rate: PKR {breakdown.basePrice}</p>
              <p>Weight charge ({formData.weight} kg): PKR {breakdown.weightCost}</p>
              <p>Distance charge ({breakdown.distance} km): PKR {breakdown.distanceCost}</p>
              <p>Package type ({breakdown.packageType}): x{breakdown.multiplier}</p>
              <p className="pt-2 font-semibold text-ink">Total: PKR {price.toLocaleString()}</p>
            </div>
            <p className="mt-4 text-xs text-ink-muted">
              Prices may vary based on actual distance and package conditions.
            </p>
          </Card>
        )}
      </div>
    </section>
  );
};

export default PriceCalculator;
