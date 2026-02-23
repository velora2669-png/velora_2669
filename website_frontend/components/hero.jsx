import React from 'react';

export default function Hero() {
  return (
    <div className="text-center max-w-2xl mb-12">
      <p className="text-sm text-orange-600 uppercase font-semibold mb-2">Vehicle Routing Solutions</p>
      <h2 className="text-3xl md:text-5xl font-extrabold mb-4 text-[#40513B]">
        Optimize Your Fleet's <span className="text-[#67c090]">Journey Home</span>
      </h2>
      <p className="text-md md:text-lg text-orange-800">
        Transform employee transportation with intelligent route optimization.
        Upload your data, and let Velora find the perfect routes for your vehicles.
      </p>
    </div>
  );
}
