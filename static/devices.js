// energy:true  -> 230V yük (aktüatör kanalına bağlanır, bus cihazı değil)
// energy:false -> KNX bus cihazı (yeşil kablo)
export const ROOM_DEVICES = [
  { id:"light", label:"Lamba", type:"light", energy:true, icon:"💡" },
  { id:"dim", label:"Dim Lamba", type:"dim", energy:true, icon:"🔆" },
  { id:"curtain", label:"Perde Motoru", type:"curtain", energy:true, icon:"🪟" },
  { id:"valve", label:"Vana", type:"valve", energy:true, icon:"🔧" },
  { id:"onoff", label:"On/Off Yük", type:"onoff", energy:true, icon:"⏻" },
  { id:"thermostat", label:"Termostat", type:"thermostat", energy:false, icon:"🌡" },
  { id:"switch", label:"KNX Anahtar", type:"switch", energy:false, icon:"🔘" },
  { id:"sensor", label:"Sensör", type:"sensor", energy:false, icon:"📡" }
];

// Hangi yük hangi aktüatör kanalına bağlanır (sunucudaki ACTUATOR_FOR ile aynı)
export const ACTUATOR_FOR = {
  light: "relay", valve: "relay", onoff: "relay",
  dim: "dimmer", curtain: "curtain_actuator"
};

export const CATEGORY_LABEL = {
  relay: "Switch Aktüatör",
  dimmer: "Dimmer Aktüatör",
  curtain_actuator: "Jalüzi/Perde Aktüatörü",
  power_supply: "Power Supply",
  interface: "IP Interface",
  router: "IP Router",
  line_coupler: "Line Coupler",
  input: "Binary Input"
};

// busMa: varsayılan bus akımı (mA) - datasheet ile doğrulanmalı
// psuMa: power supply çıkış akımı (mA)
export const PANEL_PRODUCTS = [
  { id:"psu160", name:"KNX Power Supply 160mA", category:"power_supply", moduleWidth:2, channels:1, psuMa:160, color:"#2563eb" },
  { id:"psu320", name:"KNX Power Supply 320mA", category:"power_supply", moduleWidth:4, channels:1, psuMa:320, color:"#2563eb" },
  { id:"psu640", name:"KNX Power Supply 640mA", category:"power_supply", moduleWidth:4, channels:1, psuMa:640, color:"#2563eb" },
  { id:"psu1280", name:"KNX Power Supply 1280mA", category:"power_supply", moduleWidth:6, channels:1, psuMa:1280, color:"#1d4ed8" },
  { id:"ip-interface", name:"KNX IP Interface", category:"interface", moduleWidth:2, channels:1, busMa:10, color:"#7c3aed" },
  { id:"ip-router", name:"KNX IP Router", category:"router", moduleWidth:2, channels:1, busMa:20, color:"#334155" },
  { id:"line-coupler", name:"KNX Line Coupler", category:"line_coupler", moduleWidth:2, channels:1, busMa:15, color:"#475569" },
  { id:"relay8", name:"Switch Aktüatör 8 Kanal", category:"relay", moduleWidth:8, channels:8, busMa:15, color:"#16a34a" },
  { id:"relay12", name:"Switch Aktüatör 12 Kanal", category:"relay", moduleWidth:12, channels:12, busMa:15, color:"#16a34a" },
  { id:"relay16", name:"Switch Aktüatör 16 Kanal", category:"relay", moduleWidth:12, channels:16, busMa:15, color:"#16a34a" },
  { id:"relay24", name:"Switch Aktüatör 24 Kanal", category:"relay", moduleWidth:12, channels:24, busMa:15, color:"#159947" },
  { id:"dimmer2", name:"Dimmer Aktüatör 2 Kanal", category:"dimmer", moduleWidth:4, channels:2, busMa:15, color:"#f97316" },
  { id:"dimmer4", name:"Dimmer Aktüatör 4 Kanal", category:"dimmer", moduleWidth:4, channels:4, busMa:15, color:"#f97316" },
  { id:"dimmer8", name:"Dimmer Aktüatör 8 Kanal", category:"dimmer", moduleWidth:6, channels:8, busMa:15, color:"#f97316" },
  { id:"curtain4", name:"Jalüzi/Perde Aktüatörü 4 Kanal", category:"curtain_actuator", moduleWidth:4, channels:4, busMa:15, color:"#0f766e" },
  { id:"curtain8", name:"Jalüzi/Perde Aktüatörü 8 Kanal", category:"curtain_actuator", moduleWidth:6, channels:8, busMa:15, color:"#0f766e" },
  { id:"binary4", name:"Binary Input 4 Kanal", category:"input", moduleWidth:2, channels:4, busMa:10, color:"#475569" },
  { id:"binary8", name:"Binary Input 8 Kanal", category:"input", moduleWidth:4, channels:8, busMa:10, color:"#475569" }
];
