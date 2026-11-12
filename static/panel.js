export function createInitialState() {
  return {
    zoom: 100,
    currentFloor: 0,
    floors: [
      {
        name: "Zemin Kat",
        rooms: [],
        collectors: [],
        panelProducts: []
      }
    ]
  };
}

export function currentFloor(state) {
  return state.floors[state.currentFloor];
}
