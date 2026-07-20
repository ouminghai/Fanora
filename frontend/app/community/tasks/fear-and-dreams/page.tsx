import FearAndDreamsTicket from "@/components/community/FearAndDreamsTicket";
import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";

export const metadata = {
  title: "FEAR and DREAMS 纪念票 | Fanora",
  description: "完成 FEAR and DREAMS 演唱会纪念任务，并为未来 NFT 纪念票领取积累资格。",
};

export default function FearAndDreamsTicketPage() {
  return <><Header3 /><FearAndDreamsTicket /><Footer1 /></>;
}
