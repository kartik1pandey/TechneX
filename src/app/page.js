import Navbar from "@/components/Navbar";
import Image from "next/image";

export default function Home() {
  return (
    <div>
      <Navbar />
      <div className="bg-[#201E43] min-h-screen flex flex-col items-center justify-center px-6 py-12">
      
      <div className="max-w-3xl text-center text-[#EEEEEE] mt-16 animate-fadeIn"> 
        <h1 className="text-4xl md:text-6xl font-extrabold mb-6 tracking-wide animate-slideIn">
          Unlock the Hidden Truth Behind Every Video!
        </h1>
        <p className="text-lg md:text-xl mb-6 leading-relaxed">
          Ever wondered what the <span className="font-semibold">real</span> audience thinks? Our AI-powered engine scrapes through every YouTube comment, slicing through the noise to deliver a 
          <span className="font-semibold"> sharp, witty, and brutally honest analysis</span>. From fan hype to hidden critiques, we decode the sentiment, highlight trends, and give you the ultimate inside scoop—because numbers lie, but comments don't.
        </p>
        <p className="text-lg md:text-xl mb-8">
          Ready to see beyond the views? Let's dive in!
        </p>
        <button className="px-8 py-4 text-lg font-bold text-[#201E43] bg-[#EEEEEE] rounded-full shadow-lg transition-all duration-300 hover:bg-[#508C9B] hover:text-[#EEEEEE] hover:scale-105">
          Get Started
        </button>
      </div>
    </div>
    </div>
    
  );
}