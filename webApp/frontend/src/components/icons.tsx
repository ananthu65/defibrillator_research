import type { ReactNode, SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 -960 960 960"
      width="24"
      height="24"
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

export const MenuIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M120-240v-80h720v80H120Zm0-200v-80h720v80H120Zm0-200v-80h720v80H120Z" />
  </Icon>
);

export const EditIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M200-200h57l391-391-57-57-391 391v57Zm-80 80v-170l528-527q12-11 26.500-17t30.500-6q16 0 31 6t26 18l55 56q12 11 17.500 26t5.500 30q0 16-5.500 30.500T817-647L290-120H120Zm640-584-56-56 56 56Zm-141 85-28-29 57 57-29-28Z" />
  </Icon>
);

export const StarIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="m354-287 126-76 126 77-33-144 111-96-146-13-58-136-58 135-146 13 111 97-33 143ZM233-120l65-281L80-590l288-25 112-265 112 265 288 25-218 189 65 281-247-149-247 149Z" />
  </Icon>
);

export const ClearIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="m336-280 144-144 144 144 56-56-144-144 144-144-56-56-144 144-144-144-56 56 144 144-144 144 56 56ZM480-80q-83 0-156-31.500T197-197q-54-54-85.500-127T80-480q0-83 31.500-156T197-763q54-54 127-85.500T480-880q83 0 156 31.500T763-763q54 54 85.500 127T880-480q0 83-31.500 156T763-197q-54 54-127 85.500T480-80Zm0-80q134 0 227-93t93-227q0-134-93-227t-227-93q-134 0-227 93t-93 227q0 134 93 227t227 93Zm0-320Z" />
  </Icon>
);

export const AttachFileIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M720-330q0 104-73 177T470-80q-104 0-177-73t-73-177v-370q0-75 52.500-127.500T400-880q75 0 127.500 52.500T580-700v350q0 46-32 78t-78 32q-46 0-78-32t-32-78v-370h80v370q0 13 8.500 21.500T470-320q13 0 21.500-8.500T500-350v-350q-1-42-29.500-71T400-800q-42 0-71 29t-29 71v370q-1 71 49 120.500T470-160q70 0 119-49.500T640-330v-390h80v390Z" />
  </Icon>
);

export const CheckIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M382-240 154-468l57-57 171 171 367-367 57 57-424 424Z" />
  </Icon>
);
