import React from 'react';

export default function Footer() {
  return (
    <footer className="w-full py-6 text-center text-orange-700">
      &copy; {new Date().getFullYear()} Velora. All rights reserved.
    </footer>
  );
}
