export const PAKISTAN_LOCATIONS = {
  Punjab: {
    Lahore: ['DHA Phase 1-9', 'Gulberg I-III', 'Johar Town', 'Model Town', 'Cantt', 'Allama Iqbal Town', 'Bahria Town', 'Garden Town', 'Faisal Town', 'Iqbal Town', 'Shadman', 'Township', 'Wapda Town', 'Valencia Town', 'Sui Gas Society', 'Muslim Town', 'Sabzazar', 'Raiwind Road'],
    Faisalabad: ['Samanabad', 'Peoples Colony', 'Gulberg', 'Jinnah Colony', 'Madina Town', 'Susan Road', 'Millat Town', 'D Ground', 'Sargodha Road', 'Kotwali Road'],
    Rawalpindi: ['Saddar', 'Bahria Town', 'PWD', 'Satellite Town', 'Chaklala', 'Westridge', 'Gulzar-e-Quaid', 'DHA', 'Morgah', 'Adiala Road'],
    Multan: ['Cantt', 'Gulgasht', 'New Multan', 'Bosan Road', 'Shah Rukn-e-Alam Colony', 'Model Town', 'Sher Shah Road', 'Vehari Road'],
    Gujranwala: ['Civil Lines', 'Satellite Town', 'Model Town', 'DC Colony', 'Peoples Colony', 'Rahwali Cantt', 'GT Road'],
    Sialkot: ['Cantt', 'Pasrur Road', 'Paris Road', 'Allama Iqbal Road', 'Defence Road', 'Kutchery Road'],
    Bahawalpur: ['Cantt', 'Model Town A', 'Model Town B', 'Satellite Town', 'Civil Lines'],
    Sargodha: ['Satellite Town', 'University Road', 'Cantt', 'Jinnah Colony'],
    Gujrat: ['GT Road', 'Civil Lines', 'Rehman Pura', 'Model Town'],
    Sahiwal: ['Farid Town', 'Civil Lines', 'Cantt', 'High Street'],
    Kasur: ['City Area', 'GT Road', 'Railway Road'],
    Jhelum: ['Civil Lines', 'Satellite Town', 'Cantt'],
    Sheikhupura: ['City Area', 'GT Road', 'Faisalabad Road'],
    Rahim_Yar_Khan: ['Civil Lines', 'Model Town', 'Sadiqabad Road'],
  },
  Sindh: {
    Karachi: ['Clifton', 'DHA Phase 1-8', 'Gulshan-e-Iqbal', 'North Nazimabad', 'Saddar', 'Gulistan-e-Johar', 'Malir', 'Korangi', 'Bahria Town', 'Scheme 33', 'PECHS', 'Tariq Road', 'Nazimabad', 'Federal B Area', 'Landhi', 'Shah Faisal Colony', 'Clifton Block 2-9'],
    Hyderabad: ['Latifabad', 'Qasimabad', 'Cantonment', 'City Area', 'Auto Bhan Road', 'Hali Road'],
    Sukkur: ['City Area', 'Barrage Colony', 'Military Road', 'Airport Road'],
    Larkana: ['Civil Lines', 'Bunder Road', 'Station Road'],
    Mirpurkhas: ['City Area', 'Satellite Town', 'Hyderabad Road'],
    Nawabshah: ['City Area', 'Sakrand Road'],
    Jamshoro: ['City Area', 'University Area'],
  },
  'Khyber Pakhtunkhwa': {
    Peshawar: ['Saddar', 'Hayatabad', 'University Town', 'Cantt', 'Gulbahar', 'Bara Road', 'GT Road', 'Board Bazaar', 'Dalazak Road'],
    Mardan: ['City Area', 'Sheikh Maltoon Town', 'Cantt'],
    Abbottabad: ['Mandian', 'Supply', 'Jinnahabad', 'Cantt'],
    Swat: ['Mingora', 'Saidu Sharif', 'Bahrain', 'Malam Jabba'],
    Mansehra: ['City Area', 'KTS'],
    Kohat: ['City Area', 'Cantt'],
    Dera_Ismail_Khan: ['City Area', 'Circular Road'],
  },
  Balochistan: {
    Quetta: ['Cantt', 'Satellite Town', 'Jinnah Town', 'Shahbaz Town', 'Samungli Road', 'Brewery Road'],
    Gwadar: ['City Area', 'Sangar Housing Scheme', 'New Town'],
    Turbat: ['City Area', 'Airport Road'],
    Khuzdar: ['City Area'],
    Chaman: ['City Area', 'Border Area'],
  },
  'Islamabad Capital Territory': {
    Islamabad: ['F-6', 'F-7', 'F-8', 'F-10', 'F-11', 'G-6', 'G-7', 'G-8', 'G-9', 'G-10', 'G-11', 'I-8', 'I-9', 'I-10', 'E-7', 'E-11', 'Blue Area', 'DHA', 'Bahria Town', 'PWD', 'Diplomatic Enclave'],
  },
  'Azad Kashmir': {
    Muzaffarabad: ['City Area', 'Chatter', 'Lower Plate'],
    'Mirpur AJK': ['City Area', 'Sector A', 'Sector B', 'Sector C', 'Sector D'],
    Kotli: ['City Area'],
    Rawalakot: ['City Area'],
  },
  'Gilgit-Baltistan': {
    Gilgit: ['City Area', 'Jutial', 'Danyor'],
    Skardu: ['City Area', 'Satpara'],
    Hunza: ['Karimabad', 'Aliabad'],
  }
};

/**
 * Get all provinces
 */
export const getProvinces = () => {
  return Object.keys(PAKISTAN_LOCATIONS).sort();
};

/**
 * Get cities for a province
 */
export const getCitiesByProvince = (province) => {
  if (!province || !PAKISTAN_LOCATIONS[province]) return [];
  return Object.keys(PAKISTAN_LOCATIONS[province]).sort();
};

/**
 * Get areas for a city
 */
export const getAreasByCity = (province, city) => {
  if (!province || !city || !PAKISTAN_LOCATIONS[province] || !PAKISTAN_LOCATIONS[province][city]) {
    return [];
  }
  return PAKISTAN_LOCATIONS[province][city].sort();
};

/**
 * Get all cities (flat list)
 */
export const getAllCities = () => {
  const cities = [];
  Object.values(PAKISTAN_LOCATIONS).forEach(provinceData => {
    cities.push(...Object.keys(provinceData));
  });
  return [...new Set(cities)].sort();
};

/**
 * Search locations by query (autocomplete-like)
 */
export const searchLocations = (query) => {
  if (!query || query.length < 2) return [];
  
  const results = [];
  const searchTerm = query.toLowerCase();
  
  Object.entries(PAKISTAN_LOCATIONS).forEach(([province, cities]) => {
    Object.entries(cities).forEach(([city, areas]) => {
      // Match city
      if (city.toLowerCase().includes(searchTerm)) {
        results.push({
          type: 'city',
          province,
          city,
          area: null,
          displayText: `${city}, ${province}`,
          fullAddress: `${city}, ${province}, Pakistan`
        });
      }
      
      // Match areas
      areas.forEach(area => {
        if (area.toLowerCase().includes(searchTerm)) {
          results.push({
            type: 'area',
            province,
            city,
            area,
            displayText: `${area}, ${city}`,
            fullAddress: `${area}, ${city}, ${province}, Pakistan`
          });
        }
      });
    });
  });
  
  return results.slice(0, 10);
};

/**
 * Search by province name
 */
export const searchByProvince = (query) => {
  if (!query) return [];
  const searchTerm = query.toLowerCase();
  return Object.keys(PAKISTAN_LOCATIONS).filter(p => 
    p.toLowerCase().includes(searchTerm)
  );
};

/**
 * Find province for a city
 */
export const findProvinceByCity = (cityName) => {
  for (const [province, cities] of Object.entries(PAKISTAN_LOCATIONS)) {
    if (cities[cityName]) return province;
  }
  return null;
};

/**
 * Get location hierarchy
 */
export const getLocationHierarchy = (city, area = null) => {
  const province = findProvinceByCity(city);
  if (!province) return null;
  
  return {
    province,
    city,
    area,
    fullAddress: area 
      ? `${area}, ${city}, ${province}, Pakistan`
      : `${city}, ${province}, Pakistan`
  };
};

/**
 * Validate location
 */
export const validateLocation = (province, city, area = null) => {
  if (!province || !PAKISTAN_LOCATIONS[province]) {
    return { valid: false, error: 'Invalid province' };
  }
  
  if (!city || !PAKISTAN_LOCATIONS[province][city]) {
    return { valid: false, error: 'Invalid city for this province' };
  }
  
  if (area && !PAKISTAN_LOCATIONS[province][city].includes(area)) {
    return { valid: false, error: 'Invalid area for this city' };
  }
  
  return { valid: true };
};

/**
 * Get distance estimation (placeholder - you can enhance this)
 */
const CITY_DISTANCES = {
  'Lahore-Karachi': 1200,
  'Lahore-Islamabad': 375,
  'Lahore-Faisalabad': 130,
  'Lahore-Multan': 340,
  'Karachi-Islamabad': 1400,
  'Karachi-Hyderabad': 160,
  'Islamabad-Peshawar': 180,
  'Rawalpindi-Islamabad': 15,
};

export const estimateDistance = (fromCity, toCity) => {
  if (fromCity === toCity) return 0;
  
  const key1 = `${fromCity}-${toCity}`;
  const key2 = `${toCity}-${fromCity}`;
  
  return CITY_DISTANCES[key1] || CITY_DISTANCES[key2] || 500; // Default 500km
};

export default {
  PAKISTAN_LOCATIONS,
  getProvinces,
  getCitiesByProvince,
  getAreasByCity,
  getAllCities,
  searchLocations,
  searchByProvince,
  findProvinceByCity,
  getLocationHierarchy,
  validateLocation,
  estimateDistance
};
