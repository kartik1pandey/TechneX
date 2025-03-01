
'use client'
import React, { useState } from 'react'
import Link from 'next/link';

export default function Navbar() {
    const [menuOpen, setMenuOpen] = useState(false);

    const toggleMenu = () => {
        setMenuOpen(!menuOpen);
    };
    return (

        <div className="font-fell bg-[#201E43]">
            <nav className="bg-[#201E43]">
                <div className="flex justify-between items-center p-4 lg:hidden">
                    <button className="lg:hidden text-white hover:text-violet-600" onClick={toggleMenu}>
                        <span className="text-xl">&#9776;</span>
                    </button>
                </div>


                <ul >
                    <div className = "flex flex-row justify-between">
                    <div><li className = "p-2 m-2 text-bold text-[1.75rem] text-white cursor-pointer font-bold"><Link href="/">YT Sentiment</Link></li></div>
                    <div className={`lg:flex ${menuOpen ? 'block' : 'hidden'} flex-col lg:flex-row justify-center items-center`}>
                        <li className="p-2 m-2 text-bold text-[1.25rem] text-white hover:text-violet-600 cursor-pointer transition"><Link href="/">Home</Link></li>
                        <li className="p-2 m-2 text-bold text-[1.25rem] text-white hover:text-violet-600 cursor-pointer transition">Analysis</li>

                        <li className="p-2 m-2 text-bold text-[1.25rem] text-white hover:text-violet-600 cursor-pointer transition"><Link href="/contact">Contact</Link></li>
                        <li className="p-2 m-2 text-bold text-[1.25rem] text-white hover:text-violet-600 cursor-pointer transition">Login</li>
                    </div>
                    </div>
                    


                </ul>

            </nav>
        </div>
    );
}
