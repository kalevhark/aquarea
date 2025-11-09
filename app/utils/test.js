const add = arr => {
    // console.log(typeof(arr));
    return arr.filter((word) => word > 1);
}

let x = [1, 2, 3];
// console.log(add(x));

const names = ["JC63", "Bob132", "Ursula89", "Ben96"];
const greatIDs = names
  .map((name) => parseInt(name.match(/\d+/)[0], 10))
  .filter((id, idx, arr) => {
    console.log(id, idx, arr);
  });

console.log(greatIDs);